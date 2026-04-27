# Ritter

Self-hosted receipt-splitting app. Upload receipt photos, OCR extracts line items, split costs between participants, settle balances.

## Stack

- **Backend:** FastAPI + SQLAlchemy (async) + PostgreSQL
- **Frontend:** React + Vite + TypeScript
- **OCR:** Veryfi (pluggable provider)
- **Deploy:** Docker Compose, single image (nginx + supervisord + FastAPI)

## Features

- Upload receipt images/PDFs, auto-extract line items via OCR
- Per-line allocation between participants
- Settle balances between users
- API key auth for programmatic upload (Discord bot, n8n, etc.)
- Admin user seeded on first start

## Quick start

```bash
cp .env.example .env       # fill in Veryfi creds
docker compose up -d
```

App on `http://localhost:80`. Default admin: `admin` / `changeme` (change `ADMIN_PASSWORD` in `docker-compose.yml`).

## Configuration

Set via env vars (see `.env.example` and `docker-compose.yml`):

| Var | Purpose |
|-----|---------|
| `DATABASE_URL` | Postgres async URL |
| `SECRET_KEY` | JWT signing — change in prod |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Seeded admin |
| `OCR_PROVIDER` | `veryfi` |
| `VERYFI_*` | Veryfi API creds |
| `RECEIPT_IMAGE_PATH` / `PROFILE_PICTURE_PATH` | Image storage paths |

## Local dev

```bash
pip install -r requirements.txt -r requirements-test.txt
docker compose up db -d
# create creds.json with Veryfi keys + DATABASE_URL (see .env.example)
uvicorn api.app:app --reload
```

Frontend:

```bash
cd frontend && npm install && npm run dev
```

Tests:

```bash
pytest
```

## Deploy

- `docker-compose.yml` — local/standard Docker
- `truenas_app.yaml` — TrueNAS Scale custom app

## Extensions

See [extensions/](extensions/) for Discord bot and n8n node integration.

## TODO

- add local OCR provider like [receipt-ocr](https://github.com/bhimrazy/receipt-ocr)
- add demo to readme

## License

MIT
