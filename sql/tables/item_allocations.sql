DO $$ BEGIN
    CREATE TYPE split_type AS ENUM ('equal', 'percentage', 'fraction');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS item_allocations (
    id           SERIAL PRIMARY KEY,
    line_item_id INTEGER NOT NULL REFERENCES line_items(id),
    user_id      INTEGER NOT NULL REFERENCES users(id),
    split_type   split_type NOT NULL,
    split_value  DOUBLE PRECISION,
    amount       DOUBLE PRECISION NOT NULL
);
