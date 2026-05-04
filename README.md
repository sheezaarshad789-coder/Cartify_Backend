# Cartify Backend

A FastAPI backend for Cartify, built with SQLAlchemy and Supabase-compatible Postgres support.

## Features

- User authentication endpoints (`/auth/login`, `/auth/signup`)
- Product and category listing
- Store listing and detail endpoints
- Health check endpoint
- Local SQLite development mode for quick testing

## Requirements

- Python 3.11+
- `pip` package manager
- `uvicorn`
- Dependencies listed in `requirements.txt`

## Setup

1. Create a virtual environment:

```powershell
cd D:\Cartify_Backend
python -m venv .venv
```

2. Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Copy environment configuration:

```powershell
copy .env.example backend\.env
```

5. If you want to run locally without a real Supabase/Postgres database, enable SQLite development mode:

```powershell
setx CARTIFY_DEV_SQLITE 1
```

> Note: Do not commit `.env` or `.venv` to Git.

## Run

Start the server with:

```powershell
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## API Endpoints

- `GET /health`
- `POST /auth/login`
- `POST /auth/signup`
- `GET /categories`
- `GET /stores`
- `GET /stores/{store_id}`
- `GET /products`

## Notes

- The app uses `CORS_ALLOW_ORIGINS` from environment variables.
- Admin routes are only enabled when using a real Postgres/Supabase database, not SQLite dev mode.
- Add `.venv/` to `.gitignore` before pushing to GitHub.
