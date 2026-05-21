-- ======================================================
-- RESET DO BANCO FOOTZONE (VERSÃO INTEGRAL E CORRIGIDA)
-- ======================================================

DROP DATABASE IF EXISTS marketplace_tenis;
CREATE DATABASE marketplace_tenis;
USE marketplace_tenis;

-- ======================================================
-- 1. TABELAS DE USUÁRIOS E SEGURANÇA
-- ======================================================

CREATE TABLE usuario (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    cpf VARCHAR(11) NOT NULL UNIQUE,
    telefone VARCHAR(20),
    senha_hash VARCHAR(255) NOT NULL,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    avatar MEDIUMBLOB
);

CREATE TABLE cliente (
    id_usuario INT PRIMARY KEY,
    cpf CHAR(11) NOT NULL UNIQUE,
    telefone VARCHAR(20),
    endereco VARCHAR(255),
    CONSTRAINT fk_cliente_usuario FOREIGN KEY (id_usuario) 
        REFERENCES usuario(id_usuario) ON DELETE CASCADE
);

CREATE TABLE admin (
    email VARCHAR(150) PRIMARY KEY,
    chave_acesso VARCHAR(255) NOT NULL, -- Hash SHA256
    nivel_acesso INT DEFAULT 1,
    text_departamento VARCHAR(100)
);

CREATE TABLE empresa (
    id_empresa INT AUTO_INCREMENT PRIMARY KEY,
    nome_empresa VARCHAR(150) NOT NULL,
    cnpj CHAR(14) NOT NULL UNIQUE,
    email VARCHAR(150) NOT NULL UNIQUE, 
    senha_hash VARCHAR(255) NOT NULL,    
    endereco VARCHAR(255),
    telefone VARCHAR(20),
    email_admin VARCHAR(150), 
    CONSTRAINT fk_empresa_admin 
        FOREIGN KEY (email_admin) REFERENCES admin(email) 
        ON DELETE SET NULL
);

-- ======================================================
-- 2. TABELAS DE PRODUTOS E ESTOQUE
-- ======================================================

DROP TABLE IF EXISTS produto;
CREATE TABLE produto (
    id_produto INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    descricao TEXT,
    preco DECIMAL(10,2) NOT NULL,
    tamanho VARCHAR(10),
    marca VARCHAR(100),
    categoria VARCHAR(50), -- Categoria inserida de forma direta (Casual, Corrida, etc.)
    id_empresa INT NOT NULL,
    imagem LONGBLOB,       -- Bytes da foto salvos nativamente via BLOB
    CONSTRAINT fk_produto_empresa FOREIGN KEY (id_empresa) 
        REFERENCES empresa(id_empresa) ON DELETE CASCADE
);

CREATE TABLE produto_imagem (
    id_imagem INT AUTO_INCREMENT PRIMARY KEY,
    id_produto INT NOT NULL,
    url VARCHAR(255) NOT NULL,
    CONSTRAINT fk_img_prod FOREIGN KEY (id_produto) 
        REFERENCES produto(id_produto) ON DELETE CASCADE
);

-- ======================================================
-- 3. INTERAÇÃO: FAVORITOS, CARRINHO E AVALIAÇÕES
-- ======================================================

CREATE TABLE favorito (
    id_favorito INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    id_produto INT NOT NULL,
    data_adicionado DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id_cliente, id_produto),
    CONSTRAINT fk_fav_cli FOREIGN KEY (id_cliente) REFERENCES cliente(id_usuario) ON DELETE CASCADE,
    CONSTRAINT fk_fav_prod FOREIGN KEY (id_produto) REFERENCES produto(id_produto) ON DELETE CASCADE
);

CREATE TABLE carrinho (
    id_carrinho INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL UNIQUE,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_car_cli FOREIGN KEY (id_cliente) REFERENCES cliente(id_usuario) ON DELETE CASCADE
);

CREATE TABLE item_carrinho (
    id_item INT AUTO_INCREMENT PRIMARY KEY,
    id_carrinho INT NOT NULL,
    id_produto INT NOT NULL,
    quantidade INT NOT NULL,
    CONSTRAINT fk_itemc_car FOREIGN KEY (id_carrinho) REFERENCES carrinho(id_carrinho) ON DELETE CASCADE,
    CONSTRAINT fk_itemc_prod FOREIGN KEY (id_produto) REFERENCES produto(id_produto) ON DELETE CASCADE
);

CREATE TABLE avaliacao (
    id_avaliacao INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    id_produto INT NOT NULL,
    nota INT NOT NULL CHECK (nota BETWEEN 1 AND 5),
    comentario TEXT,
    data_avaliacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_av_cli FOREIGN KEY (id_cliente) REFERENCES cliente(id_usuario) ON DELETE CASCADE,
    CONSTRAINT fk_av_prod FOREIGN KEY (id_produto) REFERENCES produto(id_produto) ON DELETE CASCADE
);

-- ======================================================
-- 4. GESTÃO DE PEDIDOS E VENDAS
-- ======================================================

CREATE TABLE pedido (
    id_pedido INT AUTO_INCREMENT PRIMARY KEY,
    data_pedido DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_pagamento DATETIME NULL,
    status ENUM('pendente','pago','cancelado') DEFAULT 'pendente',
    forma_pagamento ENUM('boleto','cartao','pix','transferencia') DEFAULT 'pix',
    total DECIMAL(10,2) NOT NULL,
    id_cliente INT NOT NULL,
    CONSTRAINT fk_ped_cli FOREIGN KEY (id_cliente) REFERENCES cliente(id_usuario) ON DELETE CASCADE
);

CREATE TABLE item_pedido (
    id_item INT AUTO_INCREMENT PRIMARY KEY,
    id_pedido INT NOT NULL,
    id_produto INT NOT NULL,
    quantidade INT NOT NULL,
    preco_unitario DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_itemp_ped FOREIGN KEY (id_pedido) REFERENCES pedido(id_pedido) ON DELETE CASCADE,
    CONSTRAINT fk_itemp_prod FOREIGN KEY (id_produto) REFERENCES produto(id_produto) ON DELETE CASCADE
);

-- ======================================================
-- 5. DADOS DE TESTE (INSERTS)
-- ======================================================

-- Usuário (Cliente) com simulação de avatar básico
INSERT INTO usuario (nome, email, cpf, telefone, senha_hash, avatar)
VALUES ('João Silva', 'joao@email.com', '12345678901', '11999999999', 'hash123', 0xFFD8FFE000104A464946);

INSERT INTO cliente (id_usuario, cpf, telefone, endereco)
VALUES (1, '12345678901', '11999999999', 'Rua A, 123');

-- Admin Base (Senha: 123456 hasheada via SHA256)
INSERT INTO admin (email, chave_acesso, text_departamento)
VALUES ('admin@footzone.com', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'TI');

-- Empresa Nike (Login: contato@nike.com / Senha: 123456 hasheada via SHA256)
INSERT INTO empresa (nome_empresa, cnpj, email, senha_hash, endereco, telefone, email_admin) 
VALUES ('Nike Store', '12345678000199', 'contato@nike.com', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'Av Central, 500', '1133334444', 'admin@footzone.com');

-- ======================================================
-- 6. CONSULTAS DE CONFERÊNCIA (SELECTS)
-- ======================================================

SHOW TABLES;
SELECT * FROM usuario;
SELECT * FROM cliente;
SELECT * FROM admin;
SELECT * FROM empresa;
SELECT * FROM produto;
SELECT * FROM produto_imagem;
SELECT * FROM favorito;
SELECT * FROM carrinho;
SELECT * FROM item_carrinho;
SELECT * FROM pedido;
SELECT * FROM item_pedido;
SELECT * FROM avaliacao;