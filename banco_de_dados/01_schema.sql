
CREATE TABLE IF NOT EXISTS usuarios (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(100) NOT NULL,
    email       VARCHAR(150) NOT NULL UNIQUE,
    senha_hash  VARCHAR(255) NOT NULL,
    criado_em   TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS livros (
    id          SERIAL PRIMARY KEY,
    titulo      VARCHAR(200) NOT NULL,
    autor       VARCHAR(150) NOT NULL,
    ano         INTEGER,
    disponivel  BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS emprestimos (
    id                       SERIAL PRIMARY KEY,
    usuario_id               INTEGER NOT NULL,
    livro_id                 INTEGER NOT NULL,
    status                   VARCHAR(20) NOT NULL DEFAULT 'ativo'
                             CHECK (status IN ('ativo', 'devolvido', 'cancelado')),
    data_emprestimo          TIMESTAMP NOT NULL DEFAULT NOW(),
    data_prevista_devolucao  TIMESTAMP NOT NULL,
    data_devolucao           TIMESTAMP
);


CREATE UNIQUE INDEX IF NOT EXISTS idx_um_emprestimo_ativo_por_livro
    ON emprestimos (livro_id) WHERE status = 'ativo';


CREATE TABLE IF NOT EXISTS notificacoes (
    id          SERIAL PRIMARY KEY,
    usuario_id  INTEGER NOT NULL,
    tipo        VARCHAR(30) NOT NULL,
    mensagem    TEXT NOT NULL,
    criado_em   TIMESTAMP NOT NULL DEFAULT NOW()
);
