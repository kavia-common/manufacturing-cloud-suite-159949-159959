manufacturing_api (FastAPI) - Local/Dev Guide

Overview
- FastAPI backend for business logic, authentication, multi-tenant data access, and real-time endpoints.
- OpenAPI docs: http://localhost:8000/docs (after starting the API)

Required tools
- Python 3.11+
- pip (and optionally virtualenv/venv)
- PostgreSQL running and reachable (see manufacturing_db README)

Environment setup
- Copy .env.example to .env and set:
  - Database:
    - POSTGRES_URL (preferred) OR POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT
  - CORS: CORS_ORIGINS=http://localhost:3000 (for Vite dev server)
  - JWT_SECRET_KEY (set a strong key for dev)
  - RUN_MIGRATIONS_ON_STARTUP=true (recommended for dev)
  - AUTO_SEED=false (set true if you want basic seed data on startup)
- Install dependencies:
  python -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt

Startup order
1) Start the database (manufacturing_db)
2) Start this API
3) Start the frontend (manufacturing_frontend)

Run migrations (optional manual invocation)
- The API will run migrations on startup if RUN_MIGRATIONS_ON_STARTUP=true.
- To invoke manually:
  python -m src.db.run_migrations upgrade head

Start the API
- Uvicorn (auto-reload):
  uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

Key environment variables
- DB:
  - POSTGRES_URL or POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB/POSTGRES_HOST/POSTGRES_PORT
  - SQL_ECHO=false
- App/HTTP:
  - CORS_ORIGINS (comma-separated; ex: http://localhost:3000)
  - CORS_ALLOW_CREDENTIALS=true
- Auth:
  - JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES
- Misc:
  - ENVIRONMENT, RUN_MIGRATIONS_ON_STARTUP, AUTO_SEED

WebSockets
- Endpoints:
  - /ws/dashboard
  - /ws/scheduler?board=default
- Clients must include:
  - Query param token=<JWT>
  - Header X-Tenant-ID=<tenant UUID>
- Note: Browsers cannot set custom headers for WebSocket handshake. For browser-based clients, consider adapting the server to also accept a tenant query param if needed.

Sample Docker Compose (reference)
version: "3.9"
services:
  db:
    image: postgres:15
    restart: unless-stopped
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: dbuser123
      POSTGRES_DB: myapp
    volumes:
      - db_data:/var/lib/postgresql/data

  api:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./:/app
    environment:
      # Prefer a single URL:
      POSTGRES_URL: postgresql://appuser:dbuser123@db:5432/myapp
      CORS_ORIGINS: http://localhost:3000
      JWT_SECRET_KEY: dev-change-me
      RUN_MIGRATIONS_ON_STARTUP: "true"
      AUTO_SEED: "false"
    depends_on:
      - db
    command: sh -c "pip install -r requirements.txt && uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload"
    ports:
      - "8000:8000"

  web:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - ../manufacturing-cloud-suite-159949-159960/manufacturing_frontend:/app
    environment:
      VITE_API_BASE_URL: http://localhost:8000
      VITE_WS_BASE_URL: ws://localhost:8000
    depends_on:
      - api
    command: sh -c "npm ci && npm run dev -- --host --port 3000"
    ports:
      - "3000:3000"

volumes:
  db_data:

Troubleshooting
- 500 or migration errors:
  - Ensure DB is running and accessible. Check POSTGRES_* env values.
  - Try manual migration: python -m src.db.run_migrations upgrade head
- 401 Unauthorized from frontend calls:
  - Ensure Authorization header contains a valid access token and X-Tenant-ID header is present.
- CORS errors:
  - Verify CORS_ORIGINS includes your frontend dev origin (http://localhost:3000).
  - If using different port/origin for frontend, update .env.
- WebSocket fails in browser:
  - The server requires X-Tenant-ID, which browsers cannot set for WS handshake. Consider adding a matching query-param support in the backend or connect from environments where custom headers are possible.
- Port already in use:
  - Change the API port (e.g., --port 8080) and update frontend .env VITE_API_BASE_URL and VITE_WS_BASE_URL accordingly.
