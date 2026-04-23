CREATE TABLE IF NOT EXISTS users (
    id                      SERIAL PRIMARY KEY,
    username                VARCHAR(255) UNIQUE NOT NULL,
    hashed_password         VARCHAR(255) NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    is_admin                BOOLEAN NOT NULL DEFAULT FALSE,
    default_participant_ids INTEGER[] NOT NULL DEFAULT '{}',
    profile_picture_path    TEXT,
    profile_picture_filename    VARCHAR(255),
    profile_picture_mimetype    VARCHAR(100),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
