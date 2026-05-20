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


#Cadastro de usuário: CREATE (CORRIGIDO)
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
        
        # Limpa o CPF para deixar apenas números (ex: '123.456.789-00' vira '12345678900')
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        # 1. Inseri na tabela 'usuario' passando o CPF e Telefone exigidos pelo NOT NULL
        query_usuario = """
            INSERT INTO usuario (nome, email, cpf, telefone, senha_hash) 
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query_usuario, (nome, email, cpf_limpo, telefone, senha_hash))
        
        # Recupera o ID gerado para o usuário
        id_novo = cursor.lastrowid
        
        # 2. Inseri na tabela 'cliente' vinculando ao ID do usuário criado
        query_cliente = """
            INSERT INTO cliente (id_usuario, cpf, telefone) 
            VALUES (%s, %s, %s)
        """
        cursor.execute(query_cliente, (id_novo, cpf_limpo, telefone))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        #erro detalhado para facilitar o debug, mas a mensagem genérica é enviada ao cliente para não expor detalhes sensíveis do banco
        print(f"Erro detalhado do Banco: {e}") 
        raise HTTPException(status_code=400, detail="Erro ao cadastrar. Verifique os dados (Email ou CPF já podem existir).")
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

# Rota para exibir o perfil do usuário (CORRIGIDA COM BUFFER)
@app.get("/perfil", response_class=HTMLResponse)
async def page_perfil(request: Request, is_user: bool = Depends(usuario_logado)):
    if not is_user:
        return RedirectResponse("/login")
    
    usuario_nome = get_usuario_logado(request)
    dados_usuario = None

    conn = conectar_banco()
    # ADICIONADO buffered=True para evitar conflitos de leitura residual no MySQL
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        # Busca todas as colunas necessárias fazendo o JOIN entre as duas tabelas pelo nome guardado no cookie
        query = """
            SELECT u.id_usuario, u.nome, u.email, u.cpf, u.telefone 
            FROM usuario u
            INNER JOIN cliente c ON u.id_usuario = c.id_usuario
            WHERE u.nome = %s
        """
        cursor.execute(query, (usuario_nome,))
        dados_usuario = cursor.fetchone()
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

# Rota para editar o perfil do usuário logado (CORREÇÃO DE BUFFER)
@app.post("/perfil/editar")
async def editar_perfil(
    request: Request, 
    nome: str = Form(...), 
    email: str = Form(...), 
    telefone: str = Form(...), 
    senha: str = Form(...)
):
    usuario_antigo = get_usuario_logado(request)
    if not usuario_antigo:
        raise HTTPException(status_code=401, detail="Usuário não autenticado")

    conn = conectar_banco()
    # ADICIONADO buffered=True para evitar o erro de "Unread result found"
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        # 1. Verificar se o novo e-mail já existe para outro usuário
        cursor.execute("SELECT id_usuario FROM usuario WHERE email = %s AND nome != %s", (email, usuario_antigo))
        email_existente = cursor.fetchone()
        if email_existente:
            raise HTTPException(status_code=400, detail="E-mail já está em uso por outro usuário")

        # 2. Localizar o ID do usuário usando o nome do cookie
        cursor.execute("SELECT id_usuario FROM usuario WHERE nome = %s", (usuario_antigo,))
        user_atual = cursor.fetchone()
        if not user_atual:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        id_usuario = user_atual['id_usuario']
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()

        # 3. Atualizar dados na tabela 'usuario'
        query_usuario = """
            UPDATE usuario 
            SET nome = %s, email = %s, telefone = %s, senha_hash = %s 
            WHERE id_usuario = %s
        """
        cursor.execute(query_usuario, (nome, email, telefone, senha_hash, id_usuario))

        # 4. Atualizar o telefone na tabela 'cliente'
        query_cliente = """
            UPDATE cliente 
            SET telefone = %s 
            WHERE id_usuario = %s
        """
        cursor.execute(query_cliente, (telefone, id_usuario))

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao atualizar perfil: {e}")
        raise HTTPException(status_code=400, detail="Erro ao atualizar perfil. Verifique os dados.")
    finally:
        cursor.close()
        conn.close()

    response = RedirectResponse(url="/perfil", status_code=303)
    response.set_cookie(key="usuario_nome", value=nome)
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)