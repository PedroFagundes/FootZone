import os
from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from db import conectar_banco

# Configuração do Router e Templates
router = APIRouter()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "..", "Template"))

# --- MIDDLEWARE DE SEGURANÇA ---
def verificar_admin(request: Request):
    if request.cookies.get("admin_logado") != "true":
        raise HTTPException(status_code=403, detail="Acesso negado")

# --- ROTA: LISTAR USUÁRIOS ---
@router.get("/admin/usuarios", response_class=HTMLResponse)
async def listar_usuarios(request: Request):
    verificar_admin(request)
    
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True)
        
        # SQL: Busca usuários e identifica o tipo (Admin/Cliente) via LEFT JOIN
        query = """
            SELECT u.id_usuario, u.nome, u.email, 
            CASE WHEN a.email IS NOT NULL THEN 'Admin' ELSE 'Cliente' END as tipo
            FROM usuario u
            LEFT JOIN admin a ON u.email = a.email
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
        if conn:
            conn.close()

# --- ROTA: EDITAR USUÁRIO ---
@router.post("/admin/usuarios/editar")
async def editar_usuario(
    request: Request,
    id_usuario: int = Form(...),
    nome: str = Form(...),
    email: str = Form(...)
):
    verificar_admin(request)
    
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        # Atualiza os dados básicos do usuário na tabela principal
        query = "UPDATE usuario SET nome = %s, email = %s WHERE id_usuario = %s"
        cursor.execute(query, (nome, email, id_usuario))
        
        conn.commit()
    except Exception as e:
        if conn: conn.rollback()
        print(f"Erro ao editar: {e}")
        raise HTTPException(status_code=400, detail="Erro ao atualizar usuário.")
    finally:
        if conn:
            conn.close()

    return RedirectResponse(url="/admin/usuarios", status_code=303)

# --- ROTA: DELETAR USUÁRIO ---
@router.post("/admin/usuarios/deletar/{id}")
async def deletar_usuario(id: int, request: Request):
    verificar_admin(request)
    
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        # O banco está com ON DELETE CASCADE, então deletar aqui remove referências em 'cliente'
        cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", (id,))
        
        conn.commit()
    except Exception as e:
        if conn: conn.rollback()
        print(f"Erro ao deletar: {e}")
        raise HTTPException(status_code=400, detail="Erro ao excluir usuário.")
    finally:
        if conn:
            conn.close()

    return RedirectResponse(url="/admin/usuarios", status_code=303)

# --- NOVA ROTA: EXIBIR CATÁLOGO DO ADMIN (ADICIONADA) ---
@router.get("/catalogoAdmin", response_class=HTMLResponse)
async def page_catalogo_admin(request: Request):
    verificar_admin(request)
    
    conn = None
    produtos = []
    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        # SQL para buscar todos os produtos juntando com a tabela de imagens trazida pelo seu amigo
        query = "SELECT p.*, pi.url FROM produto p LEFT JOIN produto_imagem pi ON p.id_produto = pi.id_produto"
        cursor.execute(query)
        produtos = cursor.fetchall()
        
        return templates.TemplateResponse("catalogoAdmin.html", {
            "request": request,
            "produtos": produtos,
            "usuario_nome": request.cookies.get("usuario_nome") or "Admin",
            "is_admin": True
        })
    except Exception as e:
        print(f"Erro ao carregar catálogo do admin: {e}")
        return HTMLResponse(content="Erro ao carregar catálogo", status_code=500)
    finally:
        if conn:
            conn.close()