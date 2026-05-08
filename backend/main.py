import os
import hashlib
import uvicorn
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from db import conectar_banco 

app = FastAPI()

from admin_users import router as admin_router # Importa o novo arquivo
app.include_router(admin_router) # Registra as rotas

print("Rotas carregadas:", [route.path for route in app.routes])

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
app.mount("/Static", StaticFiles(directory=os.path.join(BASE_DIR, "..", "Static")), name="static")
app.mount("/Imagens", StaticFiles(directory=os.path.join(BASE_DIR, "..", "Imagens")), name="imagens")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "..", "Template"))

def get_usuario_logado(request: Request):
    return request.cookies.get("usuario_nome")

# Função para verificar se o administrador está logado
# Retorna True se o cookie "admin_logado" for igual a "true"
def admin_logado(request: Request):
    return request.cookies.get("admin_logado") == "true"

# Função para verificar se o usuário está logado
# Retorna True se o cookie "usuario_nome" existir
def usuario_logado(request: Request):
    return request.cookies.get("usuario_nome") is not None

# --- ROTAS DE NAVEGAÇÃO ---

@app.get("/", response_class=HTMLResponse)
@app.get("/catalogo", response_class=HTMLResponse)
async def page_catalogo(request: Request, is_user: bool = Depends(usuario_logado)):
    if not is_user:
        return RedirectResponse("/login")
    usuario = get_usuario_logado(request)
    produtos = []
    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM produto")
        produtos = cursor.fetchall()
        cursor.close()
        conn.close()
    except: pass
    return templates.TemplateResponse(request=request, name="catalogo.html", context={"produtos": produtos, "logado": True, "usuario": usuario})

@app.get("/login", response_class=HTMLResponse)
async def page_login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/cadastro", response_class=HTMLResponse)
async def page_cadastro(request: Request):
    return templates.TemplateResponse(request=request, name="usuario.html")
#proteção de url
@app.get("/admin", response_class=HTMLResponse)
async def page_admin_login(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin.html"
    )

# --- ROTAS DE PROCESSAMENTO (POST) ---

#READ LOGIN USUÁRIO
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

#READ LOGIN ADMIN
@app.post("/login/admin")
async def login_admin(email: str = Form(...), chave: str = Form(...)):
    conn = conectar_banco()
    cursor = conn.cursor(dictionary=True)
    
    chave_hash = hashlib.sha256(chave.encode()).hexdigest()
    
    # Busca na nova tabela admin simplificada
    query = "SELECT email FROM admin WHERE email = %s AND chave_acesso = %s"
    cursor.execute(query, (email, chave_hash))
    admin = cursor.fetchone()
    
    cursor.close()
    conn.close()

    if admin:
        # MUDANÇA AQUI: O destino agora é /admin/usuarios
        response = RedirectResponse(url="/admin/usuarios", status_code=303)
        
        response.set_cookie(key="admin_logado", value="true", httponly=True)
        response.set_cookie(key="usuario_nome", value="Admin", httponly=True)
        return response
    
    raise HTTPException(status_code=401, detail="E-mail ou Chave incorretos")

#Cadastro de usuário: CREATE
@app.post("/cadastrar/usuario")
async def cadastrar_usuario(nome: str = Form(...), email: str = Form(...), cpf: str = Form(...), telefone: str = Form(...), senha: str = Form(...)):
    conn = conectar_banco()
    cursor = conn.cursor()
    try:
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        cursor.execute("INSERT INTO usuario (nome, email, senha_hash) VALUES (%s, %s, %s)", (nome, email, senha_hash))
        id_novo = cursor.lastrowid
        cursor.execute("INSERT INTO cliente (id_usuario, cpf, telefone) VALUES (%s, %s, %s)", (id_novo, ''.join(filter(str.isdigit, cpf)), telefone))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Erro ao cadastrar")
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

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)