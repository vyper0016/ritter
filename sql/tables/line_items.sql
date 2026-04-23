CREATE TABLE IF NOT EXISTS line_items (
    id          SERIAL PRIMARY KEY,
    receipt_id  INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    description TEXT,
    quantity    DOUBLE PRECISION,
    price       DOUBLE PRECISION,
    total       DOUBLE PRECISION NOT NULL,
    "order"       INTEGER,
    type        VARCHAR(100)
);
