# audit-trail

Immutable audit logging service. Tamper-evident event logging with hash chains, REST API for ingestion/search/export, retention policies, webhook notifications. FastAPI + PostgreSQL.

[![CI](https://github.com/Thebul500/audit-trail/actions/workflows/ci.yml/badge.svg)](https://github.com/Thebul500/audit-trail/actions)

## Quick Start

```bash
docker compose up -d
curl http://localhost:8000/health
```

## Installation (Development)

```bash
pip install -e .[dev]
uvicorn audit_trail.app:app --reload
```

## Usage

```bash
# Start with Docker Compose (recommended)
docker compose up -d

# Or run directly
uvicorn audit_trail.app:app --host 0.0.0.0 --port 8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/ready` | Readiness probe |

## Configuration

Environment variables (prefix `AUDIT_TRAIL_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Database connection string |
| `SECRET_KEY` | `change-me` | JWT signing key |
| `DEBUG` | `false` | Enable debug mode |
