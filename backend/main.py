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

# --- INTEGRAÇÃO DO ADMIN ---
try:
    from admin_users import router as admin_router 
    app.include_router(admin_router)
except ImportError:
    print("Aviso: admin_users.py não encontrado.")

# --- CONFIGURAÇÃO DE AMBIENTE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
app.mount("/Static", StaticFiles(directory=os.path.join(BASE_DIR, "..", "Static")), name="static")
app.mount("/Imagens", StaticFiles(directory=os.path.join(BASE_DIR, "..", "Imagens")), name="imagens")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "..", "Template"))

# --- UTILITÁRIOS ---
def get_usuario_logado(request: Request):
    return request.cookies.get("usuario_nome") or ""

# --- ROTAS DE NAVEGAÇÃO (GET) ---

@app.get("/", response_class=HTMLResponse)
@app.get("/catalogo", response_class=HTMLResponse)
async def page_catalogo(request: Request):
    usuario = get_usuario_logado(request)
    produtos = []
    avatar_b64 = None 

    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        query = "SELECT p.*, pi.url FROM produto p LEFT JOIN produto_imagem pi ON p.id_produto = pi.id_produto"
        cursor.execute(query)
        produtos = cursor.fetchall()
        
        if usuario:
            cursor.execute("SELECT avatar FROM usuario WHERE nome = %s", (usuario,))
            user_data = cursor.fetchone()
            if user_data and user_data['avatar']:
                avatar_b64 = base64.b64encode(user_data['avatar']).decode('utf-8')
            
        cursor.close()
        conn.close()
    except Exception as e: 
        print(f"Erro ao carregar catálogo: {e}")
        
    # CORREÇÃO: Passando request como argumento nomeado obrigatório
    return templates.TemplateResponse(
        request=request,
        name="catalogo.html", 
        context={
            "produtos": produtos, 
            "usuario": usuario, 
            "avatar_b64": avatar_b64, 
            "logado": usuario != ""
        }
    )

@app.get("/admin", response_class=HTMLResponse)
async def page_admin(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html", context={})

@app.get("/login", response_class=HTMLResponse)
async def page_login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})

@app.get("/login/empresa", response_class=HTMLResponse)
async def page_login_empresa(request: Request):
    return templates.TemplateResponse(request=request, name="login_empresa.html", context={})

@app.get("/cadastro", response_class=HTMLResponse)
async def page_cadastro(request: Request):
    return templates.TemplateResponse(request=request, name="usuario.html", context={})

@app.get("/empresa", response_class=HTMLResponse)
async def page_empresa(request: Request):
    return templates.TemplateResponse(request=request, name="empresa.html", context={})

@app.get("/perfil", response_class=HTMLResponse)
async def page_perfil(request: Request):
    usuario_nome = get_usuario_logado(request)
    if not usuario_nome:
        return RedirectResponse(url="/login")
    
    dados_usuario = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuario WHERE nome = %s", (usuario_nome,))
        dados_usuario = cursor.fetchone()
        if dados_usuario and dados_usuario['avatar']:
            dados_usuario['avatar_b64'] = base64.b64encode(dados_usuario['avatar']).decode('utf-8')
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro perfil: {e}")

    return templates.TemplateResponse(request=request, name="perfil.html", context={"usuario": usuario_nome, "dados_usuario": dados_usuario, "logado": True})

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
        response.set_cookie(key="usuario_nome", value=user['nome'])
        return response
    return RedirectResponse(url="/login?erro=1", status_code=303)

@app.post("/cadastrar/usuario")
async def cadastrar_usuario(nome: str = Form(...), email: str = Form(...), cpf: str = Form(...), telefone: str = Form(...), senha: str = Form(...)):
    conn = conectar_banco()
    cursor = conn.cursor()
    try:
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        caminho_foto = os.path.join(BASE_DIR, "..", "Imagens", "default_avatar.png")
        bytes_padrao = open(caminho_foto, "rb").read() if os.path.exists(caminho_foto) else b""

        cursor.execute("INSERT INTO usuario (nome, email, cpf, telefone, senha_hash, avatar) VALUES (%s, %s, %s, %s, %s, %s)", 
                       (nome, email, cpf_limpo, telefone, senha_hash, bytes_padrao))
        id_novo = cursor.lastrowid
        cursor.execute("INSERT INTO cliente (id_usuario, cpf, telefone) VALUES (%s, %s, %s)", (id_novo, cpf_limpo, telefone))
        conn.commit()
        return RedirectResponse(url="/login", status_code=303)
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Erro cadastro.")
    finally:
        cursor.close()
        conn.close()

@app.post("/cadastrar/empresa")
async def cadastrar_empresa(nome_empresa: str = Form(...), cnpj: str = Form(...), email: str = Form(...), senha: str = Form(...), telefone: str = Form(...), endereco: str = Form(...)):
    conn = conectar_banco()
    cursor = conn.cursor()
    try:
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        query = "INSERT INTO empresa (nome_empresa, cnpj, email, senha_hash, endereco, telefone) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (nome_empresa, cnpj_limpo, email, senha_hash, endereco, telefone))
        conn.commit()
        return RedirectResponse(url="/login/empresa", status_code=303)
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Erro empresa.")
    finally:
        cursor.close()
        conn.close()

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("usuario_nome")
    response.delete_cookie("admin_logado")
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)