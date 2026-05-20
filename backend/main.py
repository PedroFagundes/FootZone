import os
import hashlib
import uvicorn
import base64  
from fastapi import FastAPI, Request, Form, HTTPException, Depends, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from db import conectar_banco 

app = FastAPI()

from admin_users import router as admin_router 
app.include_router(admin_router) 

print("Rotas carregadas:", [route.path for route in app.routes])

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
app.mount("/Static", StaticFiles(directory=os.path.join(BASE_DIR, "..", "Static")), name="static")
app.mount("/Imagens", StaticFiles(directory=os.path.join(BASE_DIR, "..", "Imagens")), name="imagens")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "..", "Template"))

def get_usuario_logado(request: Request):
    return request.cookies.get("usuario_nome")

def usuario_logado(request: Request):
    return request.cookies.get("usuario_nome") is not None

# --- ROTAS DE NAVEGAÇÃO ---

@app.get("/", response_class=HTMLResponse)
@app.get("/catalogo", response_class=HTMLResponse)
async def page_catalogo(request: Request, is_user: bool = Depends(usuario_logado)):
    if not is_user:
        return RedirectResponse("/login")
    
    usuario_nome = get_usuario_logado(request)
    produtos = []
    avatar_b64 = None 

    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        cursor.execute("SELECT * FROM produto")
        produtos = cursor.fetchall()
        
        # Busca o avatar do usuário logado (que sempre terá bytes agora)
        cursor.execute("SELECT avatar FROM usuario WHERE nome = %s", (usuario_nome,))
        user_data = cursor.fetchone()
        
        if user_data and user_data['avatar']:
            avatar_b64 = base64.b64encode(user_data['avatar']).decode('utf-8')
            
        cursor.close()
        conn.close()
    except Exception as e: 
        print(f"Erro ao carregar o catálogo: {e}")
        
    return templates.TemplateResponse(
        request=request, 
        name="catalogo.html", 
        context={"produtos": produtos, "logado": True, "usuario": usuario_nome, "avatar_b64": avatar_b64}
    )

@app.get("/login", response_class=HTMLResponse)
async def page_login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/cadastro", response_class=HTMLResponse)
async def page_cadastro(request: Request):
    return templates.TemplateResponse(request=request, name="usuario.html")

@app.get("/admin", response_class=HTMLResponse)
async def page_admin_login(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html")

# --- ROTAS DE PROCESSAMENTO (POST) ---

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
        response.set_cookie(key="usuario_nome", value=user['nome'])
        return response
    return RedirectResponse(url="/login", status_code=303)

@app.post("/login/admin")
async def login_admin(email: str = Form(...), chave: str = Form(...)):
    conn = conectar_banco()
    cursor = conn.cursor(dictionary=True)
    chave_hash = hashlib.sha256(chave.encode()).hexdigest()
    query = "SELECT email FROM admin WHERE email = %s AND chave_acesso = %s"
    cursor.execute(query, (email, chave_hash))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()

    if admin:
        response = RedirectResponse(url="/admin/usuarios", status_code=303)
        response.set_cookie(key="admin_logado", value="true", httponly=True)
        response.set_cookie(key="usuario_nome", value="Admin", httponly=True)
        return response
    raise HTTPException(status_code=401, detail="E-mail ou Chave incorretos")


# CADASTRO DE USUÁRIO: SALVA O ICON.PNG POR PADRÃO NO MEDIUMBLOB DO BANCO
@app.post("/cadastrar/usuario")
async def cadastrar_usuario(
    nome: str = Form(...), 
    email: str = Form(...), 
    cpf: str = Form(...), 
    telefone: str = Form(...), 
    senha: str = Form(...)
):
    conn = conectar_banco()
    cursor = conn.cursor()
    try:
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        # Lê o arquivo que você nos enviou (salve-o como default_avatar.png na pasta Imagens)
        bytes_padrao = b""
        caminho_foto_padrao = os.path.join(BASE_DIR, "..", "Imagens", "default_avatar.png")
        
        if os.path.exists(caminho_foto_padrao):
            with open(caminho_foto_padrao, "rb") as f:
                bytes_padrao = f.read()
        else:
            print(f"Aviso: O arquivo {caminho_foto_padrao} não foi encontrado!")

        # Insere o usuário com a imagem padrão em formato binário nativo
        query_usuario = """
            INSERT INTO usuario (nome, email, cpf, telefone, senha_hash, avatar) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_usuario, (nome, email, cpf_limpo, telefone, senha_hash, bytes_padrao))
        
        id_novo = cursor.lastrowid
        
        query_cliente = """
            INSERT INTO cliente (id_usuario, cpf, telefone) 
            VALUES (%s, %s, %s)
        """
        cursor.execute(query_cliente, (id_novo, cpf_limpo, telefone))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro detalhado do Banco: {e}") 
        raise HTTPException(status_code=400, detail="Erro ao cadastrar.")
    finally:
        cursor.close()
        conn.close()
        
    return RedirectResponse(url="/login", status_code=303)

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("usuario_nome")
    response.delete_cookie("admin_logado")
    return response

@app.get("/perfil", response_class=HTMLResponse)
async def page_perfil(request: Request, is_user: bool = Depends(usuario_logado)):
    if not is_user:
        return RedirectResponse("/login")
    
    usuario_nome = get_usuario_logado(request)
    dados_usuario = None

    conn = conectar_banco()
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
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
        else:
            dados_usuario['avatar_b64'] = None
            
    except Exception as e:
        print(f"Erro ao buscar dados do perfil: {e}")
    finally:
        cursor.close()
        conn.close()

    if not dados_usuario:
        return RedirectResponse("/logout")

    return templates.TemplateResponse(
        request=request, 
        name="perfil.html", 
        context={"usuario": usuario_nome, "dados_usuario": dados_usuario, "logado": True}
    )

@app.post("/perfil/editar")
async def editar_perfil(
    request: Request, 
    nome: str = Form(...), 
    email: str = Form(...), 
    telefone: str = Form(...), 
    senha: str = Form(...),
    avatar: UploadFile = File(None)
):
    usuario_antigo = get_usuario_logado(request)
    if not usuario_antigo:
        raise HTTPException(status_code=401, detail="Usuário não autenticado")

    conn = conectar_banco()
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("SELECT id_usuario FROM usuario WHERE email = %s AND nome != %s", (email, usuario_antigo))
        email_existente = cursor.fetchone()
        if email_existente:
            raise HTTPException(status_code=400, detail="E-mail já está em uso")

        cursor.execute("SELECT id_usuario, avatar FROM usuario WHERE nome = %s", (usuario_antigo,))
        user_atual = cursor.fetchone()
        if not user_atual:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        id_usuario = user_atual['id_usuario']
        bytes_imagem = user_atual['avatar'] 
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()

        if avatar and avatar.filename:
            conteudo_arquivo = await avatar.read()
            if len(conteudo_arquivo) > 0:
                bytes_imagem = conteudo_arquivo 

        query_usuario = """
            UPDATE usuario 
            SET nome = %s, email = %s, telefone = %s, senha_hash = %s, avatar = %s 
            WHERE id_usuario = %s
        """
        cursor.execute(query_usuario, (nome, email, telefone, senha_hash, bytes_imagem, id_usuario))

        query_cliente = """
            UPDATE cliente 
            SET telefone = %s 
            WHERE id_usuario = %s
        """
        cursor.execute(query_cliente, (telefone, id_usuario))

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"ERRO CRÍTICO NO BANCO: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Erro interno: {str(e)}")
    finally:
        cursor.close()
        conn.close()

    response = RedirectResponse(url="/perfil", status_code=303)
    response.set_cookie(key="usuario_nome", value=nome)
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)