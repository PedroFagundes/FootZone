-- =====================
-- RESET DO BANCO FOOTZONE
-- =====================

-- Remove o banco se ele já existir para resetar a memória e evitar o Erro 1050 de forma limpa
DROP DATABASE IF EXISTS marketplace_tenis;

CREATE DATABASE marketplace_tenis;
USE marketplace_tenis;

-- =====================
-- TABELAS
-- =====================

CREATE TABLE usuario (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    cpf VARCHAR(11) NOT NULL UNIQUE,
    telefone VARCHAR(20),
    senha_hash VARCHAR(255) NOT NULL,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Coluna nativa adicionada diretamente na estrutura original do banco
    avatar MEDIUMBLOB
);

CREATE TABLE cliente (
    id_usuario INT PRIMARY KEY,
    cpf CHAR(11) NOT NULL UNIQUE,
    telefone VARCHAR(20),
    endereco VARCHAR(255),
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE
);

DROP TABLE IF EXISTS admin;
CREATE TABLE admin (
    email VARCHAR(150) PRIMARY KEY,
    chave_acesso VARCHAR(255) NOT NULL, -- Suporta o Hash SHA256
    nivel_acesso INT DEFAULT 1,
    departamento VARCHAR(100)
);

CREATE TABLE empresa (
    id_empresa INT AUTO_INCREMENT PRIMARY KEY,
    nome_empresa VARCHAR(150) NOT NULL,
    cnpj CHAR(14) NOT NULL UNIQUE,
    email VARCHAR(150) NOT NULL UNIQUE, -- Adicionado para Login
    senha_hash VARCHAR(255) NOT NULL,    -- Adicionado para Segurança
    endereco VARCHAR(255),
    telefone VARCHAR(20),
    email_admin VARCHAR(150), 
    
    CONSTRAINT fk_empresa_admin 
    FOREIGN KEY (email_admin) REFERENCES admin(email) 
    ON DELETE SET NULL
);

CREATE TABLE categoria (
    id_categoria INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    descricao VARCHAR(255)
);

CREATE TABLE produto (
    id_produto INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    descricao TEXT,
    preco DECIMAL(10,2) NOT NULL,
    estoque INT DEFAULT 0,
    tamanho VARCHAR(10),
    marca VARCHAR(100),
    id_categoria INT NOT NULL,
    id_empresa INT NOT NULL,
    FOREIGN KEY (id_categoria) REFERENCES categoria(id_categoria)
        ON DELETE RESTRICT,
    FOREIGN KEY (id_empresa) REFERENCES empresa(id_empresa)
        ON DELETE CASCADE
);

CREATE TABLE produto_imagem (
    id_imagem INT AUTO_INCREMENT PRIMARY KEY,
    id_produto INT NOT NULL,
    url VARCHAR(255) NOT NULL,
    FOREIGN KEY (id_produto) REFERENCES produto(id_produto)
        ON DELETE CASCADE
);

CREATE TABLE favorito (
    id_favorito INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    id_produto INT NOT NULL,
    data_adicionado DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_usuario)
        ON DELETE CASCADE,
    FOREIGN KEY (id_produto) REFERENCES produto(id_produto)
        ON DELETE CASCADE,
    UNIQUE (id_cliente, id_produto)
);

CREATE TABLE carrinho (
    id_carrinho INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL UNIQUE,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_usuario)
        ON DELETE CASCADE
);

CREATE TABLE item_carrinho (
    id_item INT AUTO_INCREMENT PRIMARY KEY,
    id_carrinho INT NOT NULL,
    id_produto INT NOT NULL,
    quantidade INT NOT NULL,
    FOREIGN KEY (id_carrinho) REFERENCES carrinho(id_carrinho)
        ON DELETE CASCADE,
    FOREIGN KEY (id_produto) REFERENCES produto(id_produto)
        ON DELETE CASCADE
);

CREATE TABLE pedido (
    id_pedido INT AUTO_INCREMENT PRIMARY KEY,
    data_pedido DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_pagamento DATETIME NULL,
    status ENUM('pendente','pago','cancelado') DEFAULT 'pendente',
    forma_pagamento ENUM('boleto','cartao','pix','transferencia') DEFAULT 'pix',
    total DECIMAL(10,2) NOT NULL,
    id_cliente INT NOT NULL,
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_usuario)
        ON DELETE CASCADE
);

CREATE TABLE item_pedido (
    id_item INT AUTO_INCREMENT PRIMARY KEY,
    id_pedido INT NOT NULL,
    id_produto INT NOT NULL,
    quantidade INT NOT NULL,
    preco_unitario DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (id_pedido) REFERENCES pedido(id_pedido)
        ON DELETE CASCADE,
    FOREIGN KEY (id_produto) REFERENCES produto(id_produto)
        ON DELETE CASCADE
);

CREATE TABLE avaliacao (
    id_avaliacao INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    id_produto INT NOT NULL,
    nota INT NOT NULL CHECK (nota BETWEEN 1 AND 5),
    comentario TEXT,
    data_avaliacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_usuario)
        ON DELETE CASCADE,
    FOREIGN KEY (id_produto) REFERENCES produto(id_produto)
        ON DELETE CASCADE
);

-- =====================
-- INSERTS
-- =====================

-- Usuario (cliente) com avatar padrão em bytes
INSERT INTO usuario (nome, email, cpf, telefone, senha_hash, avatar)
VALUES (
    'João Silva', 
    'joao@email.com', 
    '12345678901',
    '11999999999', 
    'hash123', 
    0xffd8ffe000104a46494600010200006400640000ffec00114475636b7900010004000000580000ffee000e41646f62650064c000000001ffdb0084000101010101010101010102010101020202010102020302020202020304030303030303040404040504040406060606060608080808080909090909090909090901020202030303050404050806050608090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909ffc000110800a000a003011100021101031101ffc400b9000001030501010100000000000000000000010209030607080a04050b0100010501010100000000000000000000000102030607050408100001020502030407040608020b00000001020300110405062107311208415171136191223233140981b1d153a14252239354c17282b24315160af073f192a2d2632434442555361100020103020403040806020301000000000102110304210531411206517113612232078191c1d152722314a1b162333415e142f0533516ffda000c03010002110311003f00e84d86d05299a01d07645cad25a23e627c4afe535f969f50896715413a98169a1fe1a7d4219141d4c6f94d7e5a7d421f441561e535f969f5082882ac3ca6bf2d3ea10510558794d7e5a7d420a20ab0f29afcb4fa841441565445325c3cadb2952a53089099f01c4c36528456ba027af311d6134e27514ff2c9e1cceb65a13eef6c0d61bfb8b2b9a3d91c2c8b8bddb6e9e43d8a5f9a4a8d353fcc728e6506d3ce427bfd998943564425a26991ddc0c882ace2d23cbcd4fce5b535e5a8714a91cbafda21c47d6a94e654f29afcb4fa843d2432a1e535f969f5085a212ac52d352f869f5084a216a2794d7e5a7d4216884ab0f29afcb4fa841441561e535f969f5082882ac50d35f969f5084a215318ea1084f321210a13214048820123f4c2ad092df10a7f753fd511041d284723d113c1d788d10c39a0010d1501805624020e4a42a735049fd504eaa33e00769f443924f88aba783e7c089aeb87ead7b2dd25
);

-- Cliente
INSERT INTO cliente (id_usuario, cpf, telefone, endereco)
VALUES (1, '12345678901', '11999999999', 'Rua A, 123');

-- Usuario (admin) com avatar padrão em bytes
INSERT INTO usuario (nome, email, cpf, telefone, senha_hash, avatar)
VALUES (
    'TESTE', 
    'teste@teste.com',
    '11111111111',
    '11111111111', 
    'hashadmin', 
    0xffd8ffe000104a46494600010200006400640000ffec00114475636b7900010004000000580000ffee000e41646f62650064c000000001ffdb0084000101010101010101010102010101020202010102020302020202020304030303030303040404040504040406060606060608080808080909090909090909090901020202030303050404050806050608090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909ffc000110800a000a003011100021101031101ffc400b9000001030501010100000000000000000000010209030607080a04050b0100010501010100000000000000000000000102030607050408100001020502030407040608020b00000001020300110405062107311208415171136191223233140981b1d153a14252239354c17282b24315160af073f192a2d2632434442555361100020103020403040806020301000000000102110304210531411206517113612232078191c1d152722314a1b162333415e142f0533516ffda000c03010002110311003f00e84d86d05299a01d07645cad25a23e627c4afe535f969f50896715413a98169a1fe1a7d4219141d4c6f94d7e5a7d421f441561e535f969f5082882ac3ca6bf2d3ea10510558794d7e5a7d420a20ab0f29afcb4fa841441565445325c3cadb2952a53089099f01c4c36528456ba027af311d6134e27514ff2c9e1cceb65a13eef6c0d61bfb8b2b9a3d91c2c8b8bddb6e9e43d8a5f9a4a8d353fcc728e6506d3ce427bfd998943564425a26991ddc0c882ace2d23cbcd4fce5b535e5a8714a91cbafda21c47d6a94e654f29afcb4fa843d2432a1e535f969f5085a212ac52d352f869f5084a216a2794d7e5a7d4216884ab0f29afcb4fa841441561e535f969f5082882ac50d35f969f5084a215318ea1084f321210a13214048820123f4c2ad092df10a7f753fd511041d284723d113c1d788d10c39a0010d1501805624020e4a42a735049fd504eaa33e00769f443924f88aba783e7c089aeb87ead7b2dd25
);

-- Admin
INSERT INTO admin (email, chave_acesso, departamento)
VALUES ('admin@footzone.com', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'ADMIN');

-- Empresa
INSERT INTO empresa (nome_empresa, cnpj, email, senha_hash, endereco, telefone) 
VALUES ('Nike Store', '12345678000199', 'contato@nike.com', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'Av Central, 500', '1133334444');

-- Categoria
INSERT INTO categoria (nome, descricao)
VALUES ('Corrida', 'Tênis para corrida e treino'),
       ('Casual', 'Tênis para uso diário'),
       ('Basquete', 'Tênis esportivos de quadra');

-- Produto
INSERT INTO produto (nome, descricao, preco, estoque, tamanho, marca, id_categoria, id_empresa)
VALUES ('Tênis Air Max', 'Tênis confortável para corrida', 599.90, 10, '39', 'Nike', 1, 1);
INSERT INTO produto (nome, descricao, preco, estoque, tamanho, marca, id_categoria, id_empresa)
VALUES ('Tênis Air Max', 'Tênis confortável para corrida', 599.90, 10, '42', 'Nike', 1, 1);
INSERT INTO produto (nome, descricao, preco, estoque, tamanho, marca, id_categoria, id_empresa)
VALUES ('Tênis Air Max', 'Tênis confortável para corrida', 599.90, 10, '37', 'Nike', 1, 1);

-- Produto Imagem
INSERT INTO produto_imagem (id_produto, url)
VALUES (1, 'https://imagem.com/tenis1.jpg');

-- Favorito
INSERT INTO favorito (id_cliente, id_produto)
VALUES (1, 1);

-- Carrinho
INSERT INTO carrinho (id_cliente)
VALUES (1);

INSERT INTO item_carrinho (id_carrinho, id_produto, quantidade)
VALUES (1, 1, 1);

-- Pedido
INSERT INTO pedido (id_cliente, status, forma_pagamento, total)
VALUES (1, 'pendente', 'pix', 1199.80);

-- Item Pedido
INSERT INTO item_pedido (id_pedido, id_produto, quantidade, preco_unitario)
VALUES (1, 1, 2, 599.90);

-- Avaliação
INSERT INTO avaliacao (id_cliente, id_produto, nota, comentario)
VALUES (1, 1, 5, 'Excelente produto!');

-- =====================
-- MOSTRAR TABELAS
-- =====================

SHOW TABLES;

-- =====================
-- MOSTRAR DADOS
-- =====================

SELECT * FROM usuario;
SELECT * FROM cliente;
SELECT * FROM admin;
SELECT * FROM empresa;
SELECT * FROM produto;
SELECT * FROM produto_imagem;
SELECT * FROM categoria;
SELECT * FROM favorito;
SELECT * FROM carrinho;
SELECT * FROM item_carrinho;
SELECT * FROM pedido;
SELECT * FROM item_pedido;
SELECT * FROM avaliacao;