# Contributing to audit-trail

Thank you for your interest in contributing to audit-trail! This guide covers everything you need to get started.

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 16 (or Docker)
- Git

### Dev Environment

1. Clone the repository:

```bash
git clone https://github.com/Thebul500/audit-trail.git
cd audit-trail
```

2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

3. Start PostgreSQL (using Docker):

```bash
docker compose up -d postgres
```

4. Run database migrations:

```bash
alembic upgrade head
```

5. Start the development server:

```bash
uvicorn audit_trail.app:app --reload
```

The API will be available at `http://localhost:8000`. Verify with `curl http://localhost:8000/health`.

### Environment Variables

Configuration uses the `AUDIT_TRAIL_` prefix. At minimum, set:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/audit_trail` | Database connection |
| `SECRET_KEY` | `change-me` | JWT signing key |

## Test

### Running Tests

Run the full test suite:

```bash
pytest -v
```

Run with coverage:

```bash
pytest --cov=src/audit_trail -v
```

Tests use `aiosqlite` as an in-memory backend so PostgreSQL is not required for most tests. Integration tests that require PostgreSQL are marked accordingly.

### Linting and Type Checking

The project uses `ruff` for linting, `mypy` for type checking, and `bandit` for security analysis:

```bash
ruff check src/
mypy src/audit_trail/ --ignore-missing-imports
bandit -r src/audit_trail/ -q
```

All checks must pass before submitting a PR. These same checks run in CI.

### CI Pipeline

Every push and pull request triggers the CI workflow (`.github/workflows/ci.yml`) which runs:

- `pytest` with coverage
- `ruff check` (linting)
- `mypy` (type checking)
- `bandit` (security scanning)

## Pull Request Process

### Before You Start

1. **Open an issue first** for non-trivial changes. This lets us discuss the approach before you invest time writing code.
2. **Check existing issues** to avoid duplicate work.

### Branch Naming

Use descriptive branch names:

- `fix/hash-chain-validation` for bug fixes
- `feat/export-csv` for new features
- `docs/api-examples` for documentation

### Making Changes

1. Create a feature branch from `main`:

```bash
git checkout -b feat/your-feature main
```

2. Make your changes. Follow the existing code patterns:
   - FastAPI with `async/await` for all endpoints
   - Pydantic models for request/response schemas
   - SQLAlchemy async sessions for database operations
   - Proper HTTP status codes and error responses

3. Write or update tests for your changes.

4. Ensure all checks pass locally:

```bash
pytest --cov=src/audit_trail -v
ruff check src/
mypy src/audit_trail/ --ignore-missing-imports
bandit -r src/audit_trail/ -q
```

### Submitting

1. Push your branch and open a pull request against `main`.
2. Fill in the PR description with what changed and why.
3. Ensure CI passes on your PR.
4. A maintainer will review your PR. Address any feedback by pushing additional commits.

### Code Style

- Line length: 100 characters (configured in `pyproject.toml`)
- Follow `ruff` defaults for formatting and import ordering
- Use type annotations for function signatures
- Keep functions focused and testable

### What We Look For in Reviews

- Tests cover the new or changed behavior
- No security regressions (endpoints use proper auth, no SQL injection, etc.)
- Hash chain integrity is preserved for audit events
- Error handling returns appropriate HTTP status codes
- Database migrations are backwards-compatible

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
