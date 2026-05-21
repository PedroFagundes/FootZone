import os
import base64
from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from db import conectar_banco

router = APIRouter()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "..", "Template"))

# --- MIDDLEWARE DE SEGURANÇA ---
def verificar_admin(request: Request):
    if request.cookies.get("admin_logado") != "true":
        raise HTTPException(status_code=403, detail="Acesso negado")

# --- ROTA: LISTAR USUÁRIOS (CLIENTES) ---
@router.get("/admin/usuarios", response_class=HTMLResponse)
async def listar_usuarios(request: Request):
    verificar_admin(request)
    
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True)
        
        # Puxa os dados garantindo que NULL vira string vazia
        query = """
            SELECT u.id_usuario, u.nome, u.email, 
                   COALESCE(c.cpf, '') as cpf, 
                   COALESCE(c.telefone, '') as telefone, 
                   'Cliente' as tipo
            FROM usuario u
            INNER JOIN cliente c ON u.id_usuario = c.id_usuario
            WHERE u.email NOT IN (SELECT email FROM admin)
        """
        cursor.execute(query)
        usuarios = cursor.fetchall()
        
        return templates.TemplateResponse("admin_usuarios.html", {
            "request": request, 
            "usuarios": usuarios,
            "usuario_nome": request.cookies.get("usuario_nome"),
            "is_admin": True
        })
    except Exception as e:
        print(f"Erro ao listar usuários: {e}")
        return HTMLResponse(content="Erro ao carregar banco de dados", status_code=500)
    finally:
        if conn: conn.close()

# --- ROTA: EDITAR TODOS OS PARÂMETROS DO CLIENTE (POST) ---
@router.post("/admin/usuarios/editar")
async def editar_usuario(
    request: Request,
    id_usuario: int = Form(...),
    nome: str = Form(...),
    email: str = Form(...),
    cpf: str = Form(...),
    telefone: str = Form(...)
):
    verificar_admin(request)
    
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        cpf_limpo = ''.join(filter(str.isdigit, cpf))

        # 1. Atualiza a tabela mestre usuario
        query_usuario = """
            UPDATE usuario 
            SET nome = %s, email = %s, cpf = %s, telefone = %s 
            WHERE id_usuario = %s
        """
        cursor.execute(query_usuario, (nome, email, cpf_limpo, telefone, id_usuario))
        
        # 2. Atualiza a tabela filha cliente
        query_cliente = """
            UPDATE cliente 
            SET cpf = %s, telefone = %s 
            WHERE id_usuario = %s
        """
        cursor.execute(query_cliente, (cpf_limpo, telefone, id_usuario))

        conn.commit()
        print(f"Sucesso: Admin atualizou os dados do cliente ID {id_usuario}")
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"Erro ao editar dados do cliente: {e}")
        raise HTTPException(status_code=400, detail="Erro ao atualizar dados do cliente.")
    finally:
        if conn: conn.close()

    return RedirectResponse(url="/admin/usuarios", status_code=303)

# --- ROTA: DELETAR USUÁRIO ---
@router.post("/admin/usuarios/deletar/{id}")
async def deletar_usuario(id: int, request: Request):
    verificar_admin(request)
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", (id,))
        conn.commit()
    except Exception as e:
        if conn: conn.rollback()
        print(f"Erro ao deletar: {e}")
        raise HTTPException(status_code=400, detail="Erro ao excluir usuário.")
    finally:
        if conn: conn.close()
    return RedirectResponse(url="/admin/usuarios", status_code=303)

# --- ROTA: EXIBIR CATÁLOGO DO ADMIN ---
@router.get("/catalogoAdmin", response_class=HTMLResponse)
async def page_catalogo_admin(request: Request):
    verificar_admin(request)
    conn = None
    produtos = []
    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        query = "SELECT id_produto, nome, descricao, preco, tamanho, marca, categoria, imagem FROM produto"
        cursor.execute(query)
        produtos_brutos = cursor.fetchall()
        for p in produtos_brutos:
            p['avatar_b64'] = base64.b64encode(p['imagem']).decode('utf-8') if p['imagem'] else None
            produtos.append(p)
        return templates.TemplateResponse("catalogoAdmin.html", {"request": request, "produtos": produtos, "usuario_nome": "Admin", "is_admin": True})
    except Exception as e:
        return HTMLResponse(content="Erro ao carregar catálogo", status_code=500)
    finally:
        if conn: conn.close()

# --- ROTA: EXCLUIR PRODUTO PELO ADMIN ---
@router.post("/admin/produtos/deletar/{id_produto}")
async def admin_deletar_produto(id_produto: int, request: Request):
    verificar_admin(request)
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM produto WHERE id_produto = %s", (id_produto,))
        conn.commit()
    except Exception as e:
        if conn: conn.rollback()
    finally:
        if conn: conn.close()
    return RedirectResponse(url="/catalogoAdmin", status_code=303)