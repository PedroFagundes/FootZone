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
    categoria: str = Form(...),
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

# --- ROTA: EXIBIR FORMULÁRIO DE EDIÇÃO (GET) ---
@router.get("/empresa/produtos/editar/{id_produto}", response_class=HTMLResponse)
async def page_editar_produto(id_produto: int, request: Request):
    verificar_empresa(request)
    empresa_nome = request.cookies.get("usuario_nome")
    
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        # Garante que a empresa só edite um produto que realmente pertence a ela
        query = """
            SELECT p.* FROM produto p
            INNER JOIN empresa e ON p.id_empresa = e.id_empresa
            WHERE p.id_produto = %s AND e.nome_empresa = %s
        """
        cursor.execute(query, (id_produto, empresa_nome))
        produto = cursor.fetchone()
        
        if not produto:
            raise HTTPException(status_code=404, detail="Produto não encontrado ou acesso negado.")
            
        if produto['imagem']:
            produto['avatar_b64'] = base64.b64encode(produto['imagem']).decode('utf-8')
        else:
            produto['avatar_b64'] = None
            
        return templates.TemplateResponse("editar_produto.html", {
            "request": request,
            "produto": produto,
            "usuario": empresa_nome,
            "logado": True
        })
    except Exception as e:
        print(f"Erro ao abrir edição: {e}")
        return RedirectResponse(url="/empresa/painel", status_code=303)
    finally:
        if conn: conn.close()

# --- ROTA: PROCESSAR ATUALIZAÇÃO DO PRODUTO (POST) ---
@router.post("/empresa/produtos/editar/{id_produto}")
async def editar_produto(
    id_produto: int,
    request: Request,
    nome: str = Form(...),
    marca: str = Form(...),
    categoria: str = Form(...),
    tamanho: str = Form(...),
    preco: float = Form(...),
    descricao: str = Form(None),
    imagem_arquivo: UploadFile = File(None)
):
    verificar_empresa(request)
    empresa_nome = request.cookies.get("usuario_nome")
    
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        # 1. Verifica a propriedade do produto por segurança antes do update
        query_verificar = """
            SELECT p.id_produto, p.imagem FROM produto p
            INNER JOIN empresa e ON p.id_empresa = e.id_empresa
            WHERE p.id_produto = %s AND e.nome_empresa = %s
        """
        cursor.execute(query_verificar, (id_produto, empresa_nome))
        produto_atual = cursor.fetchone()
        
        if not produto_atual:
            raise HTTPException(status_code=403, detail="Ação não permitida.")
            
        bytes_imagem = produto_atual['imagem'] # Se não enviar nova foto, mantém a antiga
        
        # 2. Se enviou uma nova foto válida, substitui os bytes
        if imagem_arquivo and imagem_arquivo.filename:
            conteudo = await imagem_arquivo.read()
            if len(conteudo) > 0:
                bytes_imagem = conteudo
                
        # 3. Executa o UPDATE dos dados modificados
        query_update = """
            UPDATE produto 
            SET nome = %s, marca = %s, categoria = %s, tamanho = %s, preco = %s, descricao = %s, imagem = %s
            WHERE id_produto = %s
        """
        cursor.execute(query_update, (nome, marca, categoria, tamanho, preco, descricao, bytes_imagem, id_produto))
        conn.commit()
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"Erro ao atualizar produto: {e}")
        raise HTTPException(status_code=400, detail="Erro ao atualizar dados do produto.")
    finally:
        if conn: conn.close()
        
    return RedirectResponse(url="/empresa/painel", status_code=303)