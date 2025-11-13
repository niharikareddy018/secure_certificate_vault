# Secure Certificate Vault – Deploy Options (Backend now in `backend/`)

This backend is a Flask app located in `backend/app.py`. You can deploy it in a few ways:
- Backend on Vercel (serverless Python) + Postgres on Supabase
- Backend on Render + Frontend on Vercel (recommended if you want persistent disk)
- Backend on Railway + Frontend on Vercel

File uploads need persistent storage. Vercel’s filesystem is ephemeral; use external storage (Supabase Storage/S3) or host backend on a platform with a mounted disk (Render/Railway) and set `UPLOAD_FOLDER`.

## What you’ll deploy
- Runtime: Vercel serverless (Python)
- Entry: `app.py` (exports `app`)
- Dependencies: `requirements.txt` at repo root
- Database: External Postgres (Supabase) via `DATABASE_URL`
- Optional: Web3 via `WEB3_PROVIDER` and `CONTRACT_ADDRESS`

## Prerequisites
- Vercel account and Vercel CLI installed
- Supabase project (if you want a persistent Postgres database)

## 1) Set up Supabase Postgres (recommended)
1. Create a new project in Supabase.
2. Go to Project Settings → Database → Connection string.
3. Copy the “Direct connection” URI. It typically looks like:
   `postgresql://postgres:<password>@<host>:5432/postgres?sslmode=require`
4. Keep it ready; you’ll set it as an env var in Vercel as `DATABASE_URL`.

Note: SQLAlchemy accepts `postgresql://...` or `postgresql+psycopg2://...`.

## 2) Configure environment variables on Vercel
Required/Useful variables:
- `DATABASE_URL` – your Supabase Postgres URI.
- `JWT_SECRET` – any long random string for JWT signing.
- `WEB3_PROVIDER` – optional HTTP RPC endpoint if using on-chain verification.
- `CONTRACT_ADDRESS` – optional, if you’ve already deployed the contract.

The app auto-sets the uploads directory to `/tmp/uploads` on Vercel.

## Option A) Backend on Vercel + DB on Supabase

### 1) Deploy to Vercel
Inside the `secure_certificate_vault` folder:

```bash
# Login once (if needed)
vercel login

# First deploy (link project and preview deployment)
vercel

# Set environment variables (one-time per project)
vercel env add DATABASE_URL
vercel env add JWT_SECRET
# Optional if using Web3
vercel env add WEB3_PROVIDER
vercel env add CONTRACT_ADDRESS

# Promote to production
vercel --prod
```

Vercel uses the top-level `vercel.json` to route everything to `app.py` using the Python runtime.

### 2) Initialize the database schema
Run the table creation once against your Supabase DB. From your machine:

```bash
# Ensure you have Python and dependencies installed locally or use a venv
# Export DATABASE_URL to your Supabase connection string
export DATABASE_URL="postgresql://..."
python init_db.py
```

This runs `db.create_all()` to create the tables defined in `models.py` on your Supabase database.

### 3) About file uploads on Vercel
The app currently stores uploaded files on the server’s filesystem and serves them back via `/uploads/<filename>`. On Vercel’s serverless runtime, the filesystem is ephemeral and not shared across invocations. That means downloads will not persist.

Recommended next step:
- Store files in an external bucket (e.g., Supabase Storage). Save the public URL or a signed URL in the database. Update the upload route to push to storage instead of writing to disk, and adjust the download route to redirect or proxy from the storage.

---

## Option B) Backend on Render + Frontend on Vercel

Render has a blueprint already: `render.yaml` at repo root. It provisions:
- A Python web service `certificate-api` using `gunicorn app:app` and a persistent disk mounted at `/data` (uploads path is `/data/uploads`).
- A Postgres database (`certdb`) and environment mapping to `DATABASE_URL`.
- An optional Ganache service (you can remove if not needed).

Steps:
1. In Render, create New → Blueprint, point to this repo, confirm regions, and deploy.
2. Check the `certificate-api` service. It will run `pip install -r backend/requirements.txt`, `python -m backend.init_db` (preDeploy), then start `gunicorn backend.app:app --bind 0.0.0.0:$PORT`.
3. Add/adjust env vars if needed: `JWT_SECRET`, `WEB3_PROVIDER`, `CONTRACT_ADDRESS`.
4. After deploy, note the backend URL like `https://certificate-api.onrender.com`.

Frontend on Vercel with same-origin API via rewrites:
1. Create a new Vercel project and set Root Directory to `secure_certificate_vault/frontend`.
2. No build command; output directory is `.`. It’s a static site.
3. In `secure_certificate_vault/frontend/vercel.json`, set the backend domain:
   - Replace `https://YOUR-BACKEND-DOMAIN` with your Render URL.
4. Deploy. The browser will call `/api/*` on your Vercel domain, which rewrites to Render. CSP `connect-src 'self'` continues to work.

---

## Option C) Backend on Railway + Frontend on Vercel

Railway setup:
1. Create a new project → Deploy from GitHub → select this repo.
2. Service settings:
   - Start command: `gunicorn backend.app:app --bind 0.0.0.0:$PORT` (also present in `Procfile`).
   - Add a volume and mount it to `/data`.
   - Add env `UPLOAD_FOLDER=/data/uploads`.
3. Add a Postgres plugin and map its connection string to `DATABASE_URL` (Railway usually exposes `DATABASE_URL` automatically).
4. One-time DB init: open a shell in the service and run `python -m backend.init_db`.
5. Note the backend URL (e.g., `https://<service>.up.railway.app`).

Frontend on Vercel with rewrites:
1. Create a Vercel project using Root Directory `secure_certificate_vault/frontend`.
2. Edit `frontend/vercel.json` and set destination to your Railway backend domain.
3. Deploy; `/api/*` will proxy to Railway.

## 6) Optional: Blockchain integration
If you want on-chain verification in production:
- Provide `WEB3_PROVIDER` (e.g., an HTTPS endpoint to an Ethereum RPC provider).
- Provide `CONTRACT_ADDRESS` for the deployed contract. The app will skip deploying on Vercel (serverless) and will only interact with an existing contract.

## Troubleshooting
- Missing dependencies: Ensure `requirements.txt` is at the project root (it is).
- 500 errors on DB access: Verify `DATABASE_URL` and that your Supabase IP allowlist permits Vercel (use “Direct connection” with SSL required).
- Uploads not found after some time: Move file storage to Supabase Storage or S3 as noted above.
 - CORS: The backend enables CORS. Using Vercel rewrites keeps API same-origin to the browser, avoiding CSP and credential issues.
- `ModuleNotFoundError: No module named 'pkg_resources'` on Render: Add `setuptools` and `wheel` to `backend/requirements.txt` (already added) and redeploy.
- Python 3.13 issues (encodings/pkg_resources): Pin a stable version by adding `runtime.txt` with `python-3.11.7` at repo root (already added).
- After dependency changes on Render: Dashboard → Service → Clear build cache → Redeploy so new packages install.

### Railway: encodings/venv errors (Dockerfile fix)
If you see errors like:

```
ModuleNotFoundError: No module named 'encodings'
program name = '/app/.venv/bin/python'
```

switch Railway to Dockerfile mode (this repo includes a `Dockerfile`):

1) In Railway → your service → Settings → Build → ensure it detects the Dockerfile (or set Build Type to Dockerfile).
2) No Start Command needed; the Dockerfile runs: `gunicorn backend.app:app --bind 0.0.0.0:$PORT`.
3) Keep your volume mount (`/data`) and env vars (`DATABASE_URL`, `JWT_SECRET`, `UPLOAD_FOLDER=/data/uploads`).
4) One-time DB init: open a shell in the running service and run:

```bash
python -m backend.init_db
```

5) Verify health:

```bash
curl -s https://<your-railway-domain>/health
```

This bypasses Nixpacks virtualenv quirks and uses the official `python:3.11-slim` runtime.

Notes specific to Railway UI:
- Build → Set Build Type to Dockerfile (not Nixpacks) so the encodings error is avoided.
- Settings → Start Command: clear any override so Dockerfile CMD is used.
- Networking → Port must be a number (e.g., 8000). Do not set it to `$PORT` (that will cause "'$PORT' is not a valid port number").

## Structure
- `app.py` – Flask app (entrypoint for Vercel)
- `config.py` – configuration and env defaults
- `models.py` – SQLAlchemy models
- `init_db.py` – one-time table creation script
- `frontend/` – static frontend assets
- `requirements.txt` – legacy root deps (not used by Render/Railway)
- `backend/` – backend service package
   - `app.py`, `config.py`, `models.py`, `init_db.py`, `requirements.txt`, `CertificateVerification.sol`
   - served via `gunicorn backend.app:app`
- `vercel.json` – if you host backend on Vercel, see legacy notes below
- `Procfile` – Default start command for platforms like Railway
- `frontend/vercel.json` – Vercel rewrites to external backend (Render/Railway)
- `render.yaml` – Render blueprint for API, DB, and optional Ganache
- `Procfile` – Default start command for platforms like Railway

---

## Quick start: Railway backend

1) Fork or connect this repo in Railway → New Project → Deploy from GitHub.
2) Variables:
    - Add Postgres plugin; DATABASE_URL will be set automatically.
    - Set `JWT_SECRET` and `UPLOAD_FOLDER=/data/uploads`.
3) Volumes: Add a volume and mount to `/data`.
4) Deploy:
   - Recommended: let Railway detect the Dockerfile in this repo (fixes encodings/venv issues).
   - Alternative (legacy): allow Nixpacks to use the `Procfile` to run `gunicorn backend.app:app`.
5) Initialize DB once:

```bash
# In Railway service shell
python -m backend.init_db
```

6) Frontend: Deploy `secure_certificate_vault/frontend` to Vercel and set `frontend/vercel.json` destination to your Railway URL.

## Quick start: Render backend

1) In Render, use Blueprint and select this repo (uses `render.yaml`).
2) It will create:
    - Web service `certificate-api` (Python, gunicorn)
    - Postgres database (bound to `DATABASE_URL`)
    - Persistent disk mounted at `/data`
3) After first deploy, the preDeploy runs `python -m backend.init_db`.
4) Frontend: Deploy `secure_certificate_vault/frontend` on Vercel and point rewrites to your Render URL.

## Environment variables

Required
- `DATABASE_URL`: Postgres connection string
   - Render: injected from the `certdb` database binding
   - Railway: injected by the Postgres plugin
   - Supabase: copy Direct connection string (SSL required), e.g.
      - `postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres?sslmode=require`
- `JWT_SECRET`: long random string used for JWT signing

Recommended
- `UPLOAD_FOLDER`: `/data/uploads` on Render/Railway; Vercel will default to `/tmp/uploads` (ephemeral)

Optional (blockchain)
- `WEB3_PROVIDER`: HTTPS RPC endpoint
- `CONTRACT_ADDRESS`: address of the deployed smart contract
- `GANACHE_HOST`, `GANACHE_PORT`: used only if `WEB3_PROVIDER` is not provided

See `.env.example` for a template.

## Database URL examples

- Generic Postgres (SSL):
   `postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require`
- SQLAlchemy + psycopg2 explicit:
   `postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require`
- Supabase (Direct):
   `postgresql://postgres:<password>@<host>:5432/postgres?sslmode=require`

## Post-deploy checks

Health
```bash
curl -s https://<your-backend-domain>/ | jq .
```

Auth and API
```bash
# Register
curl -s -X POST https://<your-backend-domain>/api/register \
   -H 'Content-Type: application/json' \
   -d '{"email":"u@example.com","password":"pass","role":"issuer"}' | jq .

# Login
TOKEN=$(curl -s -X POST https://<your-backend-domain>/api/login \
   -H 'Content-Type: application/json' \
   -d '{"email":"u@example.com","password":"pass"}' | jq -r .access_token)

# Me
curl -s https://<your-backend-domain>/api/me -H "Authorization: Bearer $TOKEN" | jq .
```
