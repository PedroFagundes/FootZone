import os
import hashlib
import uvicorn
import base64
import time  # IMPORTANTE: Para o cálculo de tempo manual
from fastapi import FastAPI, Request, Form, HTTPException, Depends, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from db import conectar_banco 

# --- CONFIGURAÇÕES DE SESSÃO ---
# Tempo de sessão (10s para teste, mude para 1800 para 30 min depois)
SESSION_TIMEOUT = 10

app = FastAPI()

# --- INTEGRAÇÃO DO ADMIN E DA EMPRESA ---
try:
    from admin_users import router as admin_router 
    app.include_router(admin_router)
except ImportError:
    print("Aviso: admin_users.py não encontrado.")

try:
    from empresa_produtos import router as empresa_router 
    app.include_router(empresa_router)
except ImportError:
    print("Aviso: empresa_produtos.py não encontrado.")

# --- CONFIGURAÇÃO DE AMBIENTE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
app.mount("/Static", StaticFiles(directory=os.path.join(BASE_DIR, "..", "Static")), name="static")
app.mount("/Imagens", StaticFiles(directory=os.path.join(BASE_DIR, "..", "Imagens")), name="imagens")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "..", "Template"))

# --- UTILITÁRIOS ---
def get_usuario_logado(request: Request):
    usuario = request.cookies.get("usuario_nome")
    ultimo_acesso = request.cookies.get("ultimo_acesso")

    # Se não tiver cookie de nome ou de tempo, não está logado
    if not usuario or not ultimo_acesso:
        return ""

    # CÁLCULO MANUAL DE TIMEOUT (Independente do navegador)
    tempo_inatividade = int(time.time()) - int(ultimo_acesso)
    if tempo_inatividade > SESSION_TIMEOUT:
        return "" # Tempo expirou
        
    return usuario

# --- ROTAS DE NAVEGAÇÃO (GET) ---

@app.get("/", response_class=HTMLResponse)
@app.get("/catalogo", response_class=HTMLResponse)
async def page_catalogo(request: Request, busca: str = None):
    usuario_nome = get_usuario_logado(request)
    
    if not usuario_nome:
        return RedirectResponse(url="/login", status_code=303)
        
    produtos = []
    avatar_b64 = None 

    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        # BARRA DE PESQUISA INTEGRADA
        if busca:
            query = """
                SELECT id_produto, nome, descricao, preco, tamanho, marca, categoria, imagem 
                FROM produto 
                WHERE nome LIKE %s OR marca LIKE %s OR categoria LIKE %s
            """
            val = (f"%{busca}%", f"%{busca}%", f"%{busca}%")
            cursor.execute(query, val)
        else:
            query = "SELECT id_produto, nome, descricao, preco, tamanho, marca, categoria, imagem FROM produto"
            cursor.execute(query)
            
        produtos_brutos = cursor.fetchall()
        for p in produtos_brutos:
            p['avatar_b64'] = base64.b64encode(p['imagem']).decode('utf-8') if p['imagem'] else None
            produtos.append(p)
        
        cursor.execute("SELECT avatar FROM usuario WHERE nome = %s", (usuario_nome,))
        user_data = cursor.fetchone()
        if user_data and user_data['avatar']:
            avatar_b64 = base64.b64encode(user_data['avatar']).decode('utf-8')
            
        cursor.close()
        conn.close()
    except Exception as e: 
        print(f"Erro no catálogo: {e}")
        
    response = templates.TemplateResponse(
        request=request, 
        name="catalogo.html", 
        context={
            "produtos": produtos, "logado": True, "usuario": usuario_nome, 
            "avatar_b64": avatar_b64, "busca": busca
        }
    )
    
    # RENOVAÇÃO DO CARIMBO DE TEMPO (Garante que os 10s resetem ao navegar)
    response.set_cookie(key="ultimo_acesso", value=str(int(time.time())), httponly=True, path="/")
    return response

@app.get("/perfil", response_class=HTMLResponse)
async def page_perfil(request: Request):
    usuario_nome = get_usuario_logado(request)
    if not usuario_nome:
        return RedirectResponse(url="/login", status_code=303)
    
    dados_usuario = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        query = """
            SELECT u.id_usuario, u.nome, u.email, u.cpf, u.telefone, u.avatar 
            FROM usuario u
            INNER JOIN cliente c ON u.id_usuario = c.id_usuario
            WHERE u.nome = %s
        """
        cursor.execute(query, (usuario_nome,))
        dados_usuario = cursor.fetchone()
        if dados_usuario and dados_usuario['avatar']:
            dados_usuario['avatar_b64'] = base64.b64encode(dados_usuario['avatar']).decode('utf-8')
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro perfil: {e}")

    if not dados_usuario:
        return RedirectResponse(url="/logout", status_code=303)

    response = templates.TemplateResponse(
        request=request, name="perfil.html", 
        context={"usuario": usuario_nome, "dados_usuario": dados_usuario, "logado": True}
    )
    # RENOVAÇÃO DO CARIMBO NO PERFIL
    response.set_cookie(key="ultimo_acesso", value=str(int(time.time())), httponly=True, path="/")
    return response

# --- PROCESSAMENTO DE DADOS (POST) ---

@app.post("/login/usuario")
async def login_usuario(email: str = Form(...), senha: str = Form(...)):
    conn = conectar_banco()
    cursor = conn.cursor(dictionary=True)
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    cursor.execute("SELECT nome FROM usuario WHERE email = %s AND senha_hash = %s", (email, senha_hash))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user:
        response = RedirectResponse(url="/catalogo", status_code=303)
        response.set_cookie(key="usuario_nome", value=user['nome'], httponly=True, path="/")
        response.set_cookie(key="ultimo_acesso", value=str(int(time.time())), httponly=True, path="/")
        return response
    return RedirectResponse(url="/login?erro=1", status_code=303)

@app.post("/login/admin")
async def login_admin(email: str = Form(...), chave: str = Form(...)):
    conn = conectar_banco()
    cursor = conn.cursor(dictionary=True)
    chave_hash = hashlib.sha256(chave.encode()).hexdigest()
    cursor.execute("SELECT email FROM admin WHERE email = %s AND chave_acesso = %s", (email, chave_hash))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()

    if admin:
        response = RedirectResponse(url="/catalogoAdmin", status_code=303)
        response.set_cookie(key="admin_logado", value="true", httponly=True, path="/")
        response.set_cookie(key="usuario_nome", value="Admin", httponly=True, path="/")
        response.set_cookie(key="ultimo_acesso", value=str(int(time.time())), httponly=True, path="/")
        return response
    return RedirectResponse(url="/admin?erro=1", status_code=303)

@app.post("/login/empresa")
async def login_empresa(cnpj: str = Form(...), senha: str = Form(...)):
    conn = conectar_banco()
    cursor = conn.cursor(dictionary=True)
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    cursor.execute("SELECT nome_empresa FROM empresa WHERE cnpj = %s AND senha_hash = %s", (cnpj_limpo, senha_hash))
    empresa = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if empresa:
        response = RedirectResponse(url="/empresa/painel", status_code=303)
        response.set_cookie(key="usuario_nome", value=empresa['nome_empresa'], httponly=True, path="/")
        response.set_cookie(key="ultimo_acesso", value=str(int(time.time())), httponly=True, path="/")
        return response
    return RedirectResponse(url="/login/empresa?erro=1", status_code=303)

@app.post("/perfil/editar")
async def editar_perfil(
    request: Request, nome: str = Form(...), email: str = Form(...), 
    telefone: str = Form(...), senha: str = Form(...), avatar: UploadFile = File(None)
):
    usuario_antigo = get_usuario_logado(request)
    if not usuario_antigo: return RedirectResponse(url="/login", status_code=303)

    conn = conectar_banco()
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("SELECT id_usuario, avatar FROM usuario WHERE nome = %s", (usuario_antigo,))
        user_atual = cursor.fetchone()
        id_usuario = user_atual['id_usuario']
        bytes_imagem = user_atual['avatar'] 
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()

        if avatar and avatar.filename:
            conteudo = await avatar.read()
            if len(conteudo) > 0: bytes_imagem = conteudo 

        cursor.execute("UPDATE usuario SET nome=%s, email=%s, telefone=%s, senha_hash=%s, avatar=%s WHERE id_usuario=%s",
                       (nome, email, telefone, senha_hash, bytes_imagem, id_usuario))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    response = RedirectResponse(url="/perfil", status_code=303)
    response.set_cookie(key="usuario_nome", value=nome, httponly=True, path="/")
    response.set_cookie(key="ultimo_acesso", value=str(int(time.time())), httponly=True, path="/")
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="usuario_nome", path="/")
    response.delete_cookie(key="admin_logado", path="/")
    response.delete_cookie(key="ultimo_acesso", path="/")
    return response

# --- ROTAS DE PÁGINAS SIMPLES ---
@app.get("/login", response_class=HTMLResponse)
async def page_login(request: Request): return templates.TemplateResponse(request=request, name="login.html", context={})
@app.get("/login/empresa", response_class=HTMLResponse)
async def page_login_empresa(request: Request): return templates.TemplateResponse(request=request, name="login_empresa.html", context={})
@app.get("/cadastro", response_class=HTMLResponse)
async def page_cadastro(request: Request): return templates.TemplateResponse(request=request, name="usuario.html", context={})
@app.get("/empresa", response_class=HTMLResponse)
async def page_empresa(request: Request): return templates.TemplateResponse(request=request, name="empresa.html", context={})
@app.get("/admin", response_class=HTMLResponse)
async def page_admin_login(request: Request): return templates.TemplateResponse(request=request, name="admin.html", context={})

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)