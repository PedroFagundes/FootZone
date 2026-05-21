import os
import base64
from fastapi import APIRouter, Request, HTTPException, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from db import conectar_banco

router = APIRouter()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "..", "Template"))

# --- MIDDLEWARE DE SEGURANÇA ---
def verificar_empresa(request: Request):
    if not request.cookies.get("usuario_nome") or request.cookies.get("usuario_nome") == "Admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a empresas parceiras.")

# --- ROTA: EXIBIR PAINEL ---
@router.get("/empresa/painel", response_class=HTMLResponse)
async def painel_empresa(request: Request):
    verificar_empresa(request)
    empresa_nome = request.cookies.get("usuario_nome")
    
    conn = None
    produtos = []
    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        # SQL atualizado para trazer a nova coluna categoria
        query = """
            SELECT p.id_produto, p.nome, p.descricao, p.preco, p.tamanho, p.marca, p.categoria, p.imagem
            FROM produto p 
            INNER JOIN empresa e ON p.id_empresa = e.id_empresa
            WHERE e.nome_empresa = %s
        """
        cursor.execute(query, (empresa_nome,))
        produtos_brutos = cursor.fetchall()
        
        for p in produtos_brutos:
            if p['imagem']:
                p['avatar_b64'] = base64.b64encode(p['imagem']).decode('utf-8')
            else:
                p['avatar_b64'] = None
            produtos.append(p)
            
    except Exception as e:
        print(f"Erro ao carregar painel: {e}")
        return HTMLResponse(content="Erro interno no servidor", status_code=500)
    finally:
        if conn: 
            conn.close()

    return templates.TemplateResponse("painel_empresa.html", {
        "request": request,
        "produtos": produtos,
        "usuario": empresa_nome,
        "logado": True
    })

# --- ROTA: EXIBIR FORMULÁRIO DE CADASTRO ---
@router.get("/empresa/produtos/cadastrar", response_class=HTMLResponse)
async def page_cadastrar_produto(request: Request):
    verificar_empresa(request)
    return templates.TemplateResponse("cadastrar_produto.html", {
        "request": request,
        "usuario": request.cookies.get("usuario_nome"),
        "logado": True
    })

# --- ROTA: PROCESSAR CADASTRO DE PRODUTO (POST) ---
@router.post("/empresa/produtos/cadastrar")
async def cadastrar_produto(
    request: Request,
    nome: str = Form(...),
    descricao: str = Form(None),
    preco: float = Form(...),
    tamanho: str = Form(...),
    marca: str = Form(...),
    categoria: str = Form(...), # Recebe a categoria do formulário HTML
    imagem_arquivo: UploadFile = File(None)
):
    verificar_empresa(request)
    empresa_nome = request.cookies.get("usuario_nome")
    
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        cursor.execute("SELECT id_empresa FROM empresa WHERE nome_empresa = %s", (empresa_nome,))
        empresa = cursor.fetchone()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não localizada.")
        
        id_empresa = empresa['id_empresa']
        
        bytes_imagem = b""
        if imagem_arquivo and imagem_arquivo.filename:
            conteudo = await imagem_arquivo.read()
            if len(conteudo) > 0:
                bytes_imagem = conteudo

        # INSERT atualizado contendo o campo categoria
        query_inserir = """
            INSERT INTO produto (nome, descricao, preco, tamanho, marca, categoria, id_empresa, imagem)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_inserir, (nome, descricao, preco, tamanho, marca, categoria, id_empresa, bytes_imagem))
        conn.commit()
        
    except Exception as e:
        if conn: 
            conn.rollback()
        print(f"Erro crítico ao salvar produto: {e}")
        raise HTTPException(status_code=400, detail="Erro ao registrar produto no estoque.")
    finally:
        if conn: 
            conn.close()

    return RedirectResponse(url="/empresa/painel", status_code=303)