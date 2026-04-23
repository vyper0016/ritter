DO $$ BEGIN
    CREATE TYPE ocr_status AS ENUM ('pending', 'processing', 'done', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS receipts (
    id               SERIAL PRIMARY KEY,
    created_by_id    INTEGER NOT NULL REFERENCES users(id),
    payer_id         INTEGER NOT NULL REFERENCES users(id),
    participant_ids  INTEGER[] NOT NULL DEFAULT '{}',
    ocr_status       ocr_status NOT NULL DEFAULT 'pending',
    date             DATE,
    total            DOUBLE PRECISION,
    vendor_name      VARCHAR(255),
    raw_ocr_data     JSONB,
    settled          BOOLEAN NOT NULL DEFAULT FALSE,
    settled_at       TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    image_path       TEXT,
    image_filename   VARCHAR(255),
    image_mimetype   VARCHAR(100)
);
