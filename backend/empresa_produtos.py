import os
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from db import conectar_banco

router = APIRouter()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "..", "Template"))

# --- MIDDLEWARE DE SEGURANÇA DA EMPRESA ---
def verificar_empresa(request: Request):
    # Garante que o usuário logado é uma empresa válida monitorando o cookie
    if not request.cookies.get("usuario_nome") or request.cookies.get("usuario_nome") == "Admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a empresas parceiras.")

# --- ROTA: EXIBIR PAINEL DA EMPRESA ---
@router.get("/empresa/painel", response_class=HTMLResponse)
async def painel_empresa(request: Request):
    verificar_empresa(request)
    empresa_nome = request.cookies.get("usuario_nome")
    
    conn = None
    produtos = []
    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        # SQL: Busca apenas os produtos que pertencem a esta empresa específica
        query = """
            SELECT p.*, pi.url 
            FROM produto p 
            LEFT JOIN produto_imagem pi ON p.id_produto = pi.id_produto
            INNER JOIN empresa e ON p.id_empresa = e.id_empresa
            WHERE e.nome_empresa = %s
        """
        cursor.execute(query, (empresa_nome,))
        produtos = cursor.fetchall()
        
    except Exception as e:
        print(f"Erro ao carregar painel da empresa: {e}")
        return HTMLResponse(content="Erro ao carregar dados do banco", status_code=500)
    finally:
        if conn:
            conn.close()

    return templates.TemplateResponse("painel_empresa.html", {
        "request": request,
        "produtos": produtos,
        "usuario": empresa_nome,
        "logado": True
    })