import sqlite3
import hashlib
from config import DB_PATH


def _hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def inicializar_banco():
    with get_db_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS operadores (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            nome    TEXT NOT NULL UNIQUE,
            senha   TEXT NOT NULL,
            perfil  TEXT NOT NULL DEFAULT 'operador',
            ativo   INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS produtos (
            ean             TEXT PRIMARY KEY,
            nome            TEXT NOT NULL,
            descricao       TEXT DEFAULT '',
            preco_venda     REAL NOT NULL CHECK (preco_venda > 0),
            estoque_atual   REAL NOT NULL DEFAULT 0 CHECK (estoque_atual >= 0),
            estoque_minimo  REAL NOT NULL DEFAULT 0,
            tipo_unidade    TEXT NOT NULL DEFAULT 'unidade',
            preco_referencia REAL
        );

        CREATE TABLE IF NOT EXISTS embalagens (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            ean_embalagem    TEXT NOT NULL UNIQUE,
            produto_base_ean TEXT NOT NULL,
            tipo             TEXT NOT NULL,
            fator_conversao  REAL NOT NULL CHECK (fator_conversao > 0),
            preco_venda      REAL,
            FOREIGN KEY (produto_base_ean) REFERENCES produtos(ean) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS abertura_caixa (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            operador_id   INTEGER NOT NULL,
            data_hora_abr TEXT NOT NULL,
            data_hora_fec TEXT,
            fundo_troco   REAL NOT NULL DEFAULT 0.0,
            status        TEXT NOT NULL DEFAULT 'aberto',
            FOREIGN KEY (operador_id) REFERENCES operadores(id)
        );

        -- Garante no nivel do banco que so pode existir 1 caixa com
        -- status 'aberto' por vez, mesmo se dois processos (dois PDVs
        -- fisicos) tentarem abrir caixa ao mesmo tempo. Sem isso, uma
        -- janela de corrida entre o SELECT de verificacao e o INSERT
        -- permite dois caixas abertos simultaneamente.
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unico_caixa_aberto
            ON abertura_caixa (status)
            WHERE status = 'aberto';

        CREATE TABLE IF NOT EXISTS movimentacoes_caixa (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            caixa_id    INTEGER NOT NULL,
            operador_id INTEGER NOT NULL,
            data_hora   TEXT NOT NULL,
            tipo        TEXT NOT NULL CHECK (tipo IN ('sangria', 'suprimento')),
            valor       REAL NOT NULL CHECK (valor > 0),
            motivo      TEXT DEFAULT '',
            FOREIGN KEY (caixa_id) REFERENCES abertura_caixa(id),
            FOREIGN KEY (operador_id) REFERENCES operadores(id)
        );

        CREATE TABLE IF NOT EXISTS auditoria (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora   TEXT NOT NULL,
            operador_id INTEGER,
            operador_nome TEXT NOT NULL DEFAULT 'Sistema',
            acao        TEXT NOT NULL,
            entidade    TEXT NOT NULL,
            entidade_id TEXT DEFAULT '',
            detalhes    TEXT DEFAULT '',
            sucesso     INTEGER NOT NULL DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS idx_auditoria_data ON auditoria (data_hora DESC);
        CREATE INDEX IF NOT EXISTS idx_auditoria_entidade ON auditoria (entidade);

        CREATE TABLE IF NOT EXISTS cobrancas_pix (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            referencia      TEXT NOT NULL UNIQUE,
            payment_id      TEXT DEFAULT '',
            valor           REAL NOT NULL,
            modo            TEXT NOT NULL CHECK (modo IN ('manual', 'automatico')),
            status          TEXT NOT NULL DEFAULT 'pendente'
                            CHECK (status IN ('pendente', 'aprovado', 'expirado', 'erro', 'cancelado')),
            data_criacao    TEXT NOT NULL,
            data_atualizacao TEXT NOT NULL,
            contingencia_acionada INTEGER NOT NULL DEFAULT 0,
            motivo_falha    TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_cobrancas_status ON cobrancas_pix (status);

        CREATE TABLE IF NOT EXISTS vendas (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            caixa_id            INTEGER NOT NULL,
            operador_id         INTEGER NOT NULL,
            data_hora           TEXT NOT NULL,
            total               REAL NOT NULL,
            desconto            REAL NOT NULL DEFAULT 0.0,
            forma_pagamento     TEXT NOT NULL,
            troco               REAL DEFAULT 0.0,
            cupom_texto         TEXT NOT NULL,
            status              TEXT NOT NULL DEFAULT 'concluida',
            motivo_cancelamento TEXT DEFAULT '',
            FOREIGN KEY (caixa_id)    REFERENCES abertura_caixa(id),
            FOREIGN KEY (operador_id) REFERENCES operadores(id)
        );

        CREATE TABLE IF NOT EXISTS itens_venda (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id       INTEGER NOT NULL,
            produto_ean    TEXT NOT NULL,
            nome_exibicao  TEXT NOT NULL,
            tipo_unidade   TEXT NOT NULL DEFAULT 'unidade',
            preco_unitario REAL NOT NULL,
            qtd            REAL NOT NULL,
            desconto_item  REAL NOT NULL DEFAULT 0.0,
            preco_total    REAL NOT NULL,
            FOREIGN KEY (venda_id) REFERENCES vendas(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS nfe_pendentes (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            chave     TEXT NOT NULL UNIQUE,
            status    TEXT NOT NULL DEFAULT 'pendente',
            motivo    TEXT DEFAULT '',
            criado_em TEXT NOT NULL,
            xml_path  TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS fornecedores (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj     TEXT NOT NULL UNIQUE,
            nome     TEXT NOT NULL,
            email    TEXT DEFAULT '',
            telefone TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_ean TEXT NOT NULL,
            data_hora   TEXT NOT NULL,
            tipo        TEXT NOT NULL,
            qtd         REAL NOT NULL,
            motivo      TEXT DEFAULT '',
            operador_id INTEGER
        );
        """)

    _migrar_banco(get_db_connection())


def _migrar_banco(conn: sqlite3.Connection):
    """Adiciona colunas novas sem quebrar banco existente."""
    colunas_produtos = [
        r[1] for r in conn.execute("PRAGMA table_info(produtos)").fetchall()
    ]
    if "tipo_unidade" not in colunas_produtos:
        conn.execute(
            "ALTER TABLE produtos ADD COLUMN tipo_unidade TEXT NOT NULL DEFAULT 'unidade'"
        )
    if "preco_referencia" not in colunas_produtos:
        conn.execute("ALTER TABLE produtos ADD COLUMN preco_referencia REAL")

    colunas_itens = [
        r[1] for r in conn.execute("PRAGMA table_info(itens_venda)").fetchall()
    ]
    if "tipo_unidade" not in colunas_itens:
        conn.execute(
            "ALTER TABLE itens_venda ADD COLUMN tipo_unidade TEXT NOT NULL DEFAULT 'unidade'"
        )

    conn.commit()
