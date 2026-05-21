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

print("Rotas carregadas com sucesso:", [route.path for route in app.routes])

# --- CONFIGURAÇÃO DE AMBIENTE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
app.mount("/Static", StaticFiles(directory=os.path.join(BASE_DIR, "..", "Static")), name="static")
app.mount("/Imagens", StaticFiles(directory=os.path.join(BASE_DIR, "..", "Imagens")), name="imagens")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "..", "Template"))

# --- UTILITÁRIOS ---
def get_usuario_logado(request: Request):
    return request.cookies.get("usuario_nome") or ""

def usuario_logado(request: Request):
    return request.cookies.get("usuario_nome") is not None

# --- ROTAS DE NAVEGAÇÃO (GET) ---

@app.get("/", response_class=HTMLResponse)
@app.get("/catalogo", response_class=HTMLResponse)
async def page_catalogo(request: Request):
    usuario_nome = get_usuario_logado(request)
    
    if not usuario_nome:
        return RedirectResponse(url="/login", status_code=303)
        
    produtos = []
    avatar_b64 = None 

    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        query = "SELECT id_produto, nome, descricao, preco, tamanho, marca, categoria, imagem FROM produto"
        cursor.execute(query)
        produtos_brutos = cursor.fetchall()
        
        for p in produtos_brutos:
            if p['imagem']:
                p['avatar_b64'] = base64.b64encode(p['imagem']).decode('utf-8')
            else:
                p['avatar_b64'] = None
            produtos.append(p)
        
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
        context={
            "produtos": produtos, 
            "logado": True, 
            "usuario": usuario_nome, 
            "avatar_b64": avatar_b64
        }
    )

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

@app.get("/admin", response_class=HTMLResponse)
async def page_admin_login(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html", context={})

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
        
        if dados_usuario:
            if dados_usuario['avatar'] and len(dados_usuario['avatar']) > 0:
                dados_usuario['avatar_b64'] = base64.b64encode(dados_usuario['avatar']).decode('utf-8')
            else:
                dados_usuario['avatar_b64'] = None
                
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro perfil: {e}")

    if not dados_usuario:
        return RedirectResponse(url="/logout", status_code=303)

    return templates.TemplateResponse(
        request=request, 
        name="perfil.html", 
        context={
            "usuario": usuario_nome, 
            "dados_usuario": dados_usuario, 
            "logado": True
        }
    )

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
        return response
    return RedirectResponse(url="/login?erro=1", status_code=303)

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
        response = RedirectResponse(url="/catalogoAdmin", status_code=303)
        response.set_cookie(key="admin_logado", value="true", httponly=True, path="/")
        response.set_cookie(key="usuario_nome", value="Admin", httponly=True, path="/")
        return response
    
    return RedirectResponse(url="/admin?erro=1", status_code=303)

@app.post("/login/empresa")
async def login_empresa(cnpj: str = Form(...), senha: str = Form(...)):
    conn = conectar_banco()
    cursor = conn.cursor(dictionary=True)
    
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    
    query = "SELECT nome_empresa FROM empresa WHERE cnpj = %s AND senha_hash = %s"
    cursor.execute(query, (cnpj_limpo, senha_hash))
    empresa = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if empresa:
        response = RedirectResponse(url="/empresa/painel", status_code=303)
        response.set_cookie(key="usuario_nome", value=empresa['nome_empresa'], httponly=True, path="/")
        return response
        
    return RedirectResponse(url="/login/empresa?erro=1", status_code=303)

@app.post("/comprar/produto/{id_produto}")
async def comprar_produto(id_produto: int, request: Request):
    usuario_nome = get_usuario_logado(request)
    if not usuario_nome:
        return RedirectResponse(url="/login", status_code=303)
        
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        # 1. Recupera o ID do cliente logado
        cursor.execute("SELECT id_usuario FROM usuario WHERE nome = %s", (usuario_nome,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        id_cliente = user['id_usuario']
        
        # 2. Busca todos os detalhes do produto antes de remover do banco
        cursor.execute("SELECT nome, marca, tamanho, categoria, preco FROM produto WHERE id_produto = %s", (id_produto,))
        produto = cursor.fetchone()
        if not produto:
            raise HTTPException(status_code=404, detail="Produto indisponível.")
        
        preco_total = produto['preco']
        
        # 3. Insere o registro mestre na tabela de pedidos
        query_pedido = """
            INSERT INTO pedido (data_pedido, status, forma_pagamento, total, id_cliente)
            VALUES (CURRENT_TIMESTAMP, 'pago', 'pix', %s, %s)
        """
        cursor.execute(query_pedido, (preco_total, id_cliente))
        id_pedido = cursor.lastrowid
        
        # 4. Vincula o item comprado ao histórico de faturamento
        query_item = """
            INSERT INTO item_pedido (id_pedido, id_produto, quantidade, preco_unitario)
            VALUES (%s, %s, 1, %s)
        """
        cursor.execute(query_item, (id_pedido, id_produto, preco_total))
        
        # 5. Remove o produto da tabela para atualizar a vitrine em tempo real
        cursor.execute("DELETE FROM produto WHERE id_produto = %s", (id_produto,))
        conn.commit()
        
        # Retorna e renderiza a página de sucesso injetando os dados do comprovante
        return templates.TemplateResponse("compra_sucesso.html", {
            "request": request,
            "id_pedido": id_pedido,
            "produto_nome": produto['nome'],
            "produto_marca": produto['marca'],
            "produto_tamanho": produto['tamanho'],
            "produto_categoria": produto['categoria'],
            "produto_preco": preco_total
        })
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"Erro ao finalizar a compra: {e}")
        raise HTTPException(status_code=400, detail="Não foi possível concluir o pedido.")
    finally:
        if conn: conn.close()

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
        
        bytes_padrao = b""
        caminho_foto_padrao = os.path.join(BASE_DIR, "..", "Imagens", "icon.png")
        
        if os.path.exists(caminho_foto_padrao):
            with open(caminho_foto_padrao, "rb") as f:
                bytes_padrao = f.read()
            print("Sucesso: Imagem padrão carregada da pasta local!")
        else:
            print(f"Aviso Crítico: O arquivo {caminho_foto_padrao} não foi encontrado!")

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
        return RedirectResponse(url="/login", status_code=303)
    except Exception as e:
        conn.rollback()
        print(f"Erro detalhado do Banco: {e}")
        raise HTTPException(status_code=400, detail="Erro no cadastro.")
    finally:
        cursor.close()
        conn.close()

@app.post("/cadastrar/empresa")
async def cadastrar_empresa(
    nome_empresa: str = Form(...), 
    cnpj: str = Form(...), 
    email: str = Form(...), 
    senha: str = Form(...), 
    telefone: str = Form(...), 
    endereco: str = Form(...)
):
    conn = conectar_banco()
    cursor = conn.cursor()
    try:
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        
        query = """
            INSERT INTO empresa (nome_empresa, cnpj, email, senha_hash, endereco, telefone) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (nome_empresa, cnpj_limpo, email, senha_hash, endereco, telefone))
        conn.commit()
        return RedirectResponse(url="/login/empresa", status_code=303)
    except Exception as e:
        conn.rollback()
        print(f"Erro empresa: {e}")
        raise HTTPException(status_code=400, detail="Erro no cadastro da empresa.")
    finally:
        cursor.close()
        conn.close()

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
    response.set_cookie(key="usuario_nome", value=nome, httponly=True, path="/")
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="usuario_nome", path="/")
    response.delete_cookie(key="admin_logado", path="/")
    print("Sessão encerrada e cookies removidos.")
    return response

if __name__ == "__main__":
    import webbrowser
    from threading import Timer

    def abrir_navegador():
        webbrowser.open("http://127.0.0.1:8000/login")

    Timer(1.5, abrir_navegador).start()
    uvicorn.run(app, host="127.0.0.1", port=8000)