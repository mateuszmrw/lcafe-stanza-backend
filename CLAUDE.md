# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project: Slovo

Self-hosted LingQ clone — a language learning platform. Users upload EPUB books, the backend tokenizes them with Stanza NLP, and the reader lets them look up words, track vocabulary statuses, get translations, and (upcoming) receive grammar explanations and synonym nuance.

**Monorepo layout:**
- `apps/backend/` — FastAPI + Stanza + ARQ worker (Python 3.12, `uv`)
- `apps/web/` — Next.js 15 App Router (TypeScript, `pnpm`)
- `docs/adr/` — Architecture Decision Records (read before making structural decisions)
- `docs/architecture/` — C4 Mermaid diagrams

## Commands

### Root (Turborepo)

```bash
npm run dev        # dev servers for both apps
npm run build      # production builds
npm run lint       # lint all apps
```

### Backend (from `apps/backend/`)

```bash
uv run fastapi dev src/main.py --port 8678   # dev server
uv run pytest                                 # all tests
uv run pytest tests/path/test_file.py::TestClass::test_name  # single test
uv run ruff check src                         # lint
uv run mypy src                               # type check
uv run alembic upgrade head                   # apply migrations
uv run alembic revision --autogenerate -m "description"  # new migration
```

### Frontend (from `apps/web/`)

```bash
pnpm dev           # dev server on :3000
pnpm build         # production build
pnpm lint          # ESLint + tsc
```

### Docker (from repo root)

```bash
docker compose up  # PostgreSQL (5432) + Redis (6379) + backend (8678) + worker
```

## Architecture overview

```
Browser (Next.js 15)
    ↓ HTTP/JSON
FastAPI backend (:8678)
    ↓ SQLAlchemy async
PostgreSQL (primary store — books, pages, vocabulary, users)
    ↓ ARQ job queue
Redis (:6379)
    ↓ worker tasks
ARQ worker (tokenize_page) → Stanza NLP pipeline
    ↓ SSE events
Browser (real-time import progress)
```

**External services:**
- DeepL API — translation (multi-instance, source→target language pairs stored in DB)
- Wiktionary adapter — dictionary lookups
- OpenAI / Claude (planned) — grammar explanation and synonym nuance (ADR-001, ADR-002)

## Key design decisions

- **See `docs/adr/`** before changing NLP, LLM, or search infrastructure. ADR-001 and ADR-002 govern the upcoming grammar/synonym features.
- Vocabulary words are **keyed by surface form** (`word.lower().strip()`), not lemma. The tokenizer stores surface forms; `get_words_map` looks up by surface form. Do not change this without updating `tokenize_page`, `get_words_map`, `upsert_with_status`, and `DefinitionPanel`.
- **StanzaClient is a singleton.** Never re-instantiate it per request. It's expensive (~seconds) to initialize. Processors currently: `tokenize,pos,lemma`. `depparse` is planned (ADR-001).
- **DeepL instances** are stored in `deepl_instances` table (one row per source→target language pair). `translation.py` queries all enabled instances for the source language and fans out.
- **ARQ worker** runs as a separate process. `tokenize_page` is the only task. Pages are dispatched via `arq.create_pool` in the books upload route.

## Environment variables (`.env` in `apps/backend/`)

| Variable        | Default                   | Description                           |
| --------------- | ------------------------- | ------------------------------------- |
| `debug`         | `false`                   | SQLAlchemy echo + debug logging       |
| `languages`     | `["russian", "polish"]`   | Stanza pipelines to preload           |
| `use_gpu`       | `false`                   | CUDA for Stanza                       |
| `model_dir`     | `stanza_resources`        | Stanza model cache path               |
| `storage_root`  | `/app/storage`            | Book file uploads root                |
| `db_host`       | `localhost`               | PostgreSQL host                       |
| `db_port`       | `5432`                    | PostgreSQL port                       |
| `db_database`   | `db`                      | DB name                               |
| `db_username`   | `user`                    | DB user                               |
| `db_password`   | `password`                | DB password                           |
| `redis_url`     | `redis://localhost:6379`  | ARQ + general Redis                   |
| `jwt_secret`    | —                         | JWT signing secret (required)         |
| `deepl_api_key` | —                         | DeepL API key (optional, system-wide) |

<!-- MEMORY:START -->
# cafe-backend

_Last updated: 2026-04-15 | 0 active memories, 0 total_

_For deeper context, use memory_search, memory_related, or memory_ask tools._
<!-- MEMORY:END -->
