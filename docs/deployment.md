# Deployment Guide

## Quick Start with Docker Compose

The fastest way to run Audit Trail in production:

```bash
# Clone and configure
git clone https://github.com/your-org/audit-trail.git
cd audit-trail

# Set a strong secret key
export SECRET_KEY=$(openssl rand -hex 32)

# Start services
docker compose up -d
```

This starts the API server on port 8000 and PostgreSQL 16 on port 5432.

## Configuration

All settings are controlled via environment variables with the `AUDIT_TRAIL_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `AUDIT_TRAIL_DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/audit_trail` | Async PostgreSQL connection string |
| `AUDIT_TRAIL_SECRET_KEY` | `change-me-in-production` | JWT signing key — **must be changed** |
| `AUDIT_TRAIL_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT token lifetime |
| `AUDIT_TRAIL_DEBUG` | `false` | Enable debug mode |

## Database Setup

### Run Migrations

Alembic manages the database schema:

```bash
alembic upgrade head
```

### Production PostgreSQL

For production, use a managed PostgreSQL instance (AWS RDS, Cloud SQL, etc.) and set the connection string:

```bash
export AUDIT_TRAIL_DATABASE_URL="postgresql+asyncpg://user:password@db-host:5432/audit_trail"
```

## Authentication Setup

Before using the API, register a client and obtain a JWT token:

```bash
# 1. Register an API client
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "my-service", "scopes": ["events:read", "events:write"]}'

# Response includes the API key (store it securely — shown only once):
# {"id": "...", "name": "my-service", "api_key": "abc123..."}

# 2. Exchange the API key for a JWT token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "abc123..."}'

# Response: {"access_token": "eyJ...", "token_type": "bearer"}

# 3. Use the token in subsequent requests
curl http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer eyJ..."
```

## Running Without Docker

Install dependencies and run directly:

```bash
pip install -e .
uvicorn audit_trail.app:app --host 0.0.0.0 --port 8000
```

Ensure PostgreSQL is running and accessible at the configured `DATABASE_URL`.

## Health Check

Verify the service is running:

```bash
curl http://localhost:8000/api/v1/health
# {"status": "ok", "version": "0.1.0", "timestamp": "..."}
```

## Production Checklist

- [ ] Set a strong `AUDIT_TRAIL_SECRET_KEY` (at least 32 random bytes)
- [ ] Use a managed PostgreSQL instance with backups enabled
- [ ] Run behind a reverse proxy (nginx, Caddy) with TLS termination
- [ ] Set `AUDIT_TRAIL_DEBUG=false`
- [ ] Configure retention policies for each audit stream
- [ ] Set up monitoring on the `/api/v1/health` endpoint
- [ ] Restrict network access to the database port
