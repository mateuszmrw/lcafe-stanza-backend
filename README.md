# Cafe — Self-hosted LingQ Clone

Monorepo containing the backend NLP service and the Next.js web frontend.

## Structure

```
apps/
  backend/   FastAPI + Stanza NLP service (Python)
  web/       Next.js 15 frontend (TypeScript)
```

## Prerequisites

- Node.js 20+, npm 10+
- Python 3.12+, [uv](https://docs.astral.sh/uv/)
- Docker + Docker Compose

## Getting started

### Install JS dependencies

```bash
npm install
```

### Run everything with Docker

```bash
docker compose up
```

This starts:
- PostgreSQL on port 5432
- Python backend on port 8678

### Run individually

```bash
# Backend
cd apps/backend
uv run fastapi dev src/main.py --port 8678

# Frontend
cd apps/web
npm run dev
```

## Turbo tasks

```bash
npm run dev      # dev servers for all apps
npm run build    # production build for all apps
npm run lint     # lint all apps
```
