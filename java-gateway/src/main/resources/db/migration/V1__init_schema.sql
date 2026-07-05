-- Enable pgvector (constitution I.3 / research.md §1)
CREATE EXTENSION IF NOT EXISTS vector;

-- Tenant configuration (persona + channels + Drive) — constitution I.6
CREATE TABLE tenant_config (
    tenant_id             VARCHAR(50)  PRIMARY KEY,
    product               VARCHAR(20)  NOT NULL DEFAULT 'rockey',
    agent_first_name      VARCHAR(50)  NOT NULL,
    agent_tone            TEXT         NOT NULL,
    agent_formality       VARCHAR(20)  NOT NULL DEFAULT 'formal',
    agent_language        VARCHAR(10)  NOT NULL DEFAULT 'fr',
    channel_web_active    BOOLEAN      NOT NULL DEFAULT true,
    channel_email_active  BOOLEAN      NOT NULL DEFAULT false,
    channel_email_imap    VARCHAR(200),
    channel_email_address VARCHAR(200),
    channel_slack_active  BOOLEAN      NOT NULL DEFAULT false,
    channel_slack_channel VARCHAR(100),
    drive_folder_id       VARCHAR(100),
    drive_sync_mode       VARCHAR(20)  NOT NULL DEFAULT 'auto',
    drive_sync_cron       VARCHAR(50)  DEFAULT '0 2 * * *',
    last_sync_at          TIMESTAMP,
    last_sync_status      VARCHAR(20),
    created_at            TIMESTAMP    DEFAULT NOW()
);

-- RAG policy documents (chunks) — constitution I.3, III.6
CREATE TABLE rag_documents (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   VARCHAR(50)  NOT NULL REFERENCES tenant_config(tenant_id),
    source      VARCHAR(100) NOT NULL,
    type        VARCHAR(30)  NOT NULL
                CHECK (type IN ('policy', 'faq', 'catalogue', 'config')),
    chunk_index INTEGER      NOT NULL,
    content     TEXT         NOT NULL,
    embedding   vector(384),
    created_at  TIMESTAMP    DEFAULT NOW(),
    UNIQUE(tenant_id, source, chunk_index)
);
CREATE INDEX rag_documents_embedding_idx ON rag_documents
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_rag_tenant ON rag_documents(tenant_id);
CREATE INDEX idx_rag_type   ON rag_documents(tenant_id, type);

-- Product catalog — constitution I.3, II.2
CREATE TABLE articles (
    id                VARCHAR(20)  PRIMARY KEY,
    tenant_id         VARCHAR(50)  NOT NULL REFERENCES tenant_config(tenant_id),
    name              VARCHAR(200) NOT NULL,
    category          VARCHAR(50)  NOT NULL,
    sub_category      VARCHAR(50),
    era               VARCHAR(20),
    material          TEXT,
    price             DECIMAL(8,2) NOT NULL,
    returnable        BOOLEAN      NOT NULL DEFAULT true,
    non_return_reason VARCHAR(100),
    article_type      VARCHAR(30)  NOT NULL
                      CHECK (article_type IN ('standard','premium','piece_unique','destockage','bijou','ceinture')),
    description       TEXT,
    active            BOOLEAN      NOT NULL DEFAULT true,
    created_at        TIMESTAMP    DEFAULT NOW(),
    embedding         vector(384)
);
CREATE INDEX articles_embedding_idx ON articles
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_articles_tenant     ON articles(tenant_id);
CREATE INDEX idx_articles_returnable ON articles(tenant_id, returnable);
CREATE INDEX idx_articles_price      ON articles(tenant_id, price);

-- Orders (test seed) — constitution I.6
CREATE TABLE orders (
    id            VARCHAR(20)  PRIMARY KEY,
    tenant_id     VARCHAR(50)  NOT NULL REFERENCES tenant_config(tenant_id),
    client_email  VARCHAR(255) NOT NULL,
    client_name   VARCHAR(100) NOT NULL,
    article_id    VARCHAR(20)  REFERENCES articles(id),
    amount        DECIMAL(8,2) NOT NULL,
    status        VARCHAR(20)  NOT NULL DEFAULT 'delivered',
    order_date    DATE         NOT NULL,
    delivery_date DATE,
    created_at    TIMESTAMP    DEFAULT NOW()
);
CREATE INDEX idx_orders_tenant_email ON orders(tenant_id, client_email);

-- Return / complaint cases ("Case" in spec.md, "Dossier" here — same entity, per data-model.md)
CREATE TABLE dossiers (
    id           UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    VARCHAR(50)   NOT NULL REFERENCES tenant_config(tenant_id),
    client_email VARCHAR(255)  NOT NULL,
    order_id     VARCHAR(20)   REFERENCES orders(id),
    article_id   VARCHAR(20)   REFERENCES articles(id),
    type         VARCHAR(20)   NOT NULL CHECK (type IN ('return','complaint')),
    reason       VARCHAR(100),
    status       VARCHAR(30)   NOT NULL CHECK (status IN ('in_progress','resolved','escalated')),
    decision     VARCHAR(30)   CHECK (decision IN ('accepted','refused','escalated')),
    amount       DECIMAL(10,2),
    channel      VARCHAR(20)   CHECK (channel IN ('web','email')),
    session_id   VARCHAR(100),
    applied_rule VARCHAR(100),
    return_id    VARCHAR(50),
    refund_id    VARCHAR(50),
    ticket_id    VARCHAR(50),
    created_at   TIMESTAMP     DEFAULT NOW(),
    updated_at   TIMESTAMP     DEFAULT NOW()
);
CREATE INDEX idx_dossiers_order  ON dossiers(order_id);
CREATE INDEX idx_dossiers_status ON dossiers(tenant_id, status);

-- Customer long-term memory
CREATE TABLE client_history (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        VARCHAR(50)  NOT NULL REFERENCES tenant_config(tenant_id),
    client_email     VARCHAR(255) NOT NULL,
    return_count     INTEGER DEFAULT 0,
    complaint_count  INTEGER DEFAULT 0,
    escalation_count INTEGER DEFAULT 0,
    last_contact     TIMESTAMP,
    created_at       TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, client_email)
);
