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
    usuario = request.cookies.get("usuario_nome")
    if not usuario or usuario == "Admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a empresas parceiras.")

# --- ROTA: PAINEL DA EMPRESA ---
@router.get("/empresa/painel", response_class=HTMLResponse)
async def painel_empresa(request: Request):
    nome_empresa = request.cookies.get("usuario_nome")
    if not nome_empresa:
        return RedirectResponse(url="/login/empresa", status_code=303)

    conn = None
    produtos = []
    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        # Seleciona apenas os produtos DESTA empresa
        query = "SELECT * FROM produto WHERE marca = %s"
        cursor.execute(query, (nome_empresa,))
        produtos_brutos = cursor.fetchall()

        for p in produtos_brutos:
            if p.get('imagem'):
                p['avatar_b64'] = base64.b64encode(p['imagem']).decode('utf-8')
            else:
                p['avatar_b64'] = None
            produtos.append(p)

        return templates.TemplateResponse(
            request=request, 
            name="painel_empresa.html", 
            context={
                "produtos": produtos, 
                "usuario": nome_empresa, 
                "logado": True
            }
        )
    except Exception as e:
        print(f"Erro no painel da empresa: {e}")
        return HTMLResponse(content=f"Erro interno: {e}", status_code=500)
    finally:
        if conn: conn.close()

# --- ROTA: EXIBIR FORMULÁRIO DE CADASTRO (GET) ---
@router.get("/empresa/produtos/cadastrar", response_class=HTMLResponse)
async def page_cadastrar_produto(request: Request):
    verificar_empresa(request)
    nome_empresa = request.cookies.get("usuario_nome")
    
    return templates.TemplateResponse(
        request=request, 
        name="cadastrar_produto.html", 
        context={
            "usuario": nome_empresa, 
            "logado": True
        }
    )

# --- ROTA: PROCESSAR CADASTRO DE PRODUTO (POST) ---
@router.post("/empresa/produtos/cadastrar")
async def cadastrar_produto_post(
    request: Request,
    nome: str = Form(...),
    descricao: str = Form(None),
    preco: str = Form(...), 
    tamanho: str = Form(...),
    categoria: str = Form(...),
    valor_transporte: str = Form(None), # Campo da prova de autoria
    imagem_arquivo: UploadFile = File(None)
):
    verificar_empresa(request)
    empresa_nome = request.cookies.get("usuario_nome")
    
    conn = None
    try:
        # Tratamento do Preço para evitar erro de banco (limpeza de R$, pontos e vírgulas)
        preco_limpo = preco.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".").strip()
        preco_float = float(preco_limpo)

        # Tratamento do Valor de Transporte (Prova de Autoria)
        transporte_float = None
        if valor_transporte:
            transporte_limpo = valor_transporte.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".").strip()
            transporte_float = float(transporte_limpo)

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
            INSERT INTO produto (nome, descricao, preco, tamanho, marca, categoria, id_empresa, imagem, valor_transporte)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_inserir, (nome, descricao, preco_float, tamanho, empresa_nome, categoria, id_empresa, bytes_imagem, transporte_float))
        conn.commit()
        
        return RedirectResponse(url="/empresa/painel", status_code=303)
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"Erro ao salvar produto: {e}")
        # Captura o erro de valor fora da faixa (Out of range) para o MySQL
        if "1264" in str(e):
            return RedirectResponse(url="/empresa/produtos/cadastrar?erro=valor_limite", status_code=303)
        return RedirectResponse(url="/empresa/produtos/cadastrar?erro=1", status_code=303)
    finally:
        if conn: conn.close()

# --- ROTA: EXIBIR FORMULÁRIO DE EDIÇÃO (GET) ---
@router.get("/empresa/produtos/editar/{id_produto}", response_class=HTMLResponse)
async def page_editar_produto(id_produto: int, request: Request):
    verificar_empresa(request)
    empresa_nome = request.cookies.get("usuario_nome")
    
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        query = """
            SELECT p.* FROM produto p
            INNER JOIN empresa e ON p.id_empresa = e.id_empresa
            WHERE p.id_produto = %s AND e.nome_empresa = %s
        """
        cursor.execute(query, (id_produto, empresa_nome))
        produto = cursor.fetchone()
        
        if not produto:
            return RedirectResponse(url="/empresa/painel", status_code=303)
            
        produto['avatar_b64'] = base64.b64encode(produto['imagem']).decode('utf-8') if produto['imagem'] else None
            
        return templates.TemplateResponse(
            request=request,
            name="editar_produto.html",
            context={
                "produto": produto,
                "usuario": empresa_nome,
                "logado": True
            }
        )
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
    categoria: str = Form(...),
    tamanho: str = Form(...),
    preco: str = Form(...),
    descricao: str = Form(None),
    imagem_arquivo: UploadFile = File(None)
):
    verificar_empresa(request)
    empresa_nome = request.cookies.get("usuario_nome")
    
    conn = None
    try:
        preco_limpo = preco.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".").strip()
        preco_float = float(preco_limpo)

        conn = conectar_banco()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        cursor.execute("SELECT imagem FROM produto WHERE id_produto = %s", (id_produto,))
        produto_atual = cursor.fetchone()
        
        if not produto_atual:
            raise HTTPException(status_code=403, detail="Ação não permitida.")
            
        bytes_imagem = produto_atual['imagem']
        if imagem_arquivo and imagem_arquivo.filename:
            conteudo = await imagem_arquivo.read()
            if len(conteudo) > 0:
                bytes_imagem = conteudo
                
        query_update = """
            UPDATE produto 
            SET nome = %s, categoria = %s, tamanho = %s, preco = %s, descricao = %s, imagem = %s
            WHERE id_produto = %s
        """
        cursor.execute(query_update, (nome, categoria, tamanho, preco_float, descricao, bytes_imagem, id_produto))
        conn.commit()
        
        return RedirectResponse(url="/empresa/painel", status_code=303)

    except Exception as e:
        if conn: conn.rollback()
        print(f"Erro ao atualizar produto: {e}")
        if "1264" in str(e):
            return RedirectResponse(url=f"/empresa/produtos/editar/{id_produto}?erro=valor_limite", status_code=303)
        return RedirectResponse(url=f"/empresa/produtos/editar/{id_produto}?erro=1", status_code=303)
    finally:
        if conn: conn.close()