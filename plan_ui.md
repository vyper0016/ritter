# UI Plan: React + Vite + Tailwind SPA

## Context
Backend is a complete FastAPI JSON API with JWT auth (Bearer header), receipt upload, OCR, allocation, and settlement. No frontend exists. Goal: add a React SPA that covers all user-facing flows.

---

## Stack
- **React 18 + TypeScript** via Vite
- **Tailwind CSS** — utility-first styling
- **TanStack Query (React Query)** — server state, caching, polling
- **React Router v6** — client-side routing
- **fetch** — plain fetch with a thin typed wrapper (no axios)
- JWT stored in `localStorage`; Bearer header injected via wrapper

---

## Project Structure

```
frontend/
  src/
    api/          # typed fetch wrappers per domain (auth.ts, receipts.ts, etc.)
    components/   # AllocationEditor, ReceiptCard, OcrBadge, UserAvatar, etc.
    contexts/     # AuthContext (current user + token)
    hooks/        # useCurrentUser, useReceipts, etc.
    pages/
      LoginPage.tsx
      DashboardPage.tsx
      NewReceiptPage.tsx
      ReceiptDetailPage.tsx
      SettlePage.tsx
      AdminPage.tsx
      ProfilePage.tsx
    types.ts      # TypeScript types mirroring API response models
    main.tsx
    App.tsx       # router setup + AuthContext provider
  index.html
  vite.config.ts  # proxy /api → http://localhost:8000
  tailwind.config.ts
  package.json
  tsconfig.json
```

---

## Pages

| Page | Route | Auth | Description |
|------|-------|------|-------------|
| Login | `/login` | public | username/password → JWT |
| Dashboard | `/` | required | receipt list, filters (settled/role), upload button |
| New Receipt | `/receipts/new` | required | image upload + payer + participants (pre-filled from defaults) |
| Receipt Detail | `/receipts/:id` | required | header, OCR status (polls if pending/processing), line items, allocation editor, per-user summary |
| Settle | `/settle` | required | unsettled preview, grand totals, OCR mismatch warnings, settle actions |
| Admin | `/admin` | admin only | user list, create user form |
| Profile | `/profile` | required | set default participants, upload profile picture |

---

## Key Components

**`AllocationEditor`** (most complex) — per line item:
1. Subset of receipt participants (checkboxes)
2. Split type: `equal | percentage | fraction`
3. Value inputs (hidden for equal; % per person for percentage; numerator for fraction)
4. Inline validation (percentage sum must = 100)
5. Submit → `PUT /receipts/{id}/items/{item_id}/allocations`

**`OcrBadge`** — shows pending/processing/done/failed; React Query polls `GET /receipts/{id}` every 2s while status is pending/processing.

**`ReceiptCard`** — compact card on dashboard: vendor, date, total, ocr badge, settled chip.

**`UserAvatar`** — renders `GET /users/{id}/picture` or initials fallback.

---

## Auth Flow
1. `POST /auth/login` (form data) → `{access_token, token_type}`
2. Store token in `localStorage`
3. `AuthContext` reads token on mount, fetches `GET /users` to identify current user by decoding JWT sub (user_id)
4. All API calls inject `Authorization: Bearer <token>`
5. 401 response → clear token + redirect to `/login`

---

## API Layer (`src/api/`)

Thin typed wrappers:
```ts
// src/api/client.ts
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T>
// throws on non-2xx, injects Bearer token from localStorage
```

Domain files: `auth.ts`, `receipts.ts`, `users.ts`, `allocations.ts`, `settle.ts` — each exports typed functions matching the endpoints.

Types in `src/types.ts` mirror Pydantic response models:
```ts
interface Receipt { id: number; vendor_name: string | null; ocr_status: OcrStatus; settled: boolean; ... }
interface LineItem { id: number; description: string | null; total: number; ... }
interface Allocation { id: number; user_id: number; split_type: SplitType; amount: number; ... }
// etc.
```

---

## Dev Setup
- `vite.config.ts`: proxy `/api` prefix → `http://localhost:8000` (eliminates CORS in dev)
- Two processes: `uvicorn api.app:app --reload` + `npm run dev` in `frontend/`
- Add CORS to FastAPI for production (env-configurable allowed origin)

---

## Docker / Production

```yaml
# Add to docker-compose.yml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile   # node build → nginx serve
  ports:
    - "80:80"
  depends_on:
    - api
```

`frontend/Dockerfile`:
```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

`frontend/nginx.conf`: serve `index.html` for all routes, proxy `/api` → `http://api:8000`.

**CORS in FastAPI**: Add `CORSMiddleware` in `api/app.py` with `CORS_ORIGINS` env var (default `http://localhost:5173` for dev).

---

## Critical Files to Modify

| File | Change |
|------|--------|
| `api/app.py` | Add `CORSMiddleware` |
| `docker-compose.yml` | Add `frontend` service |
| `frontend/` | Create entire directory |

---

## Verification

1. `docker compose up db` + `uvicorn api.app:app` + `npm run dev` in `frontend/`
2. Login as admin → dashboard shows empty state
3. Upload sample receipt → card shows `pending` → polls to `done`
4. Open detail → line items populated → set equal split → summary shows per-user amounts
5. Go to Settle → preview shows receipt → "Settle all" → receipt marked settled
6. Admin page → create second user
7. `docker compose up --build` → nginx serves frontend, `/api/*` proxied to FastAPI

---

## Build Order
1. `frontend/` scaffolding (Vite init, Tailwind, router, AuthContext)
2. API client layer + types
3. Login page
4. Dashboard + receipt card
5. New receipt page (upload form)
6. Receipt detail + OCR polling
7. AllocationEditor component
8. Settle page
9. Admin + Profile pages
10. Docker + CORS wiring
