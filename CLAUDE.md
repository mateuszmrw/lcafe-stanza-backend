# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project: Slovo

Self-hosted language learning platform (LingQ-clone). Users upload EPUB/PDF books, the backend tokenizes them with Stanza NLP, and the reader lets them look up words, track vocabulary statuses, get translations, grammar explanations, and synonym nuance. Includes EPUB3 audiobook support (SMIL overlays), on-demand TTS generation, reading streaks, Anki sync, and word frequency coverage stats.

**Monorepo layout:**
- `apps/backend/` — FastAPI + Stanza + ARQ worker (Python 3.12, `uv`)
- `apps/web/` — Next.js 15 App Router (TypeScript, `pnpm`)
- `docs/adr/` — Architecture Decision Records (read before structural decisions)
- `docs/architecture/` — C4 Mermaid diagrams
- `.claude/ClaudeReference.md` — Detailed architectural reference

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
docker compose up  # PostgreSQL (5432) + Redis (6379) + backend (8678) + ARQ worker + web (4412)
```

## Architecture overview

```
Browser (Next.js 15, port 3000 / 4412 in Docker)
    ↓ HTTP/JSON + SSE
FastAPI backend (:8678)
    ↓ SQLAlchemy async (asyncpg)
PostgreSQL — books, pages, vocabulary, users, alignments, phrases, activity, streaks
    ↓ ARQ job queue
Redis (:6379) — job queue + SSE pub/sub + rate limiting + stats cache (5 min TTL)
    ↓ worker tasks
ARQ worker — tokenize_page, align_smil_audio, generate_tts_audio
    ↓ Stanza NLP / Qwen TTS
Browser (SSE for real-time import + audio alignment progress)
```

**External services:**
- DeepL API — translation (multi-instance: multiple source→target pairs in `deepl_instances` table)
- Wiktionary — dictionary lookups (pre-imported from dump via `/admin/dictionary`)
- OpenAI / Claude — grammar explanation and synonym nuance (LLM cascade: DB system key → env var)
- Qwen TTS — text-to-speech generation for books without embedded audio

## Critical design decisions

Read `.claude/ClaudeReference.md` before making structural decisions. The non-negotiable rules:

- **Vocabulary keyed by lemma** (since migration 0042). `words.word` stores `token.l.lower().strip()`. `content_pages.lemma_map` (JSONB) maps `{surface → lemma}` for read-time enrichment. Frontend sends `token.l` for status changes. Pre-0042 pages (lemma_map=null) fall back to surface-form lookup.
- **StanzaClient is a singleton** — initialized once at startup, never per-request. Current processors: `tokenize,pos,lemma`.
- **Redis lives in `app.state`** — created in `lifespan`, accessed via `get_redis(request)` and `get_arq_pool(request)` dependencies.
- **API keys are AES-256 encrypted** in the DB using `db_encryption_key`. Never store plaintext.
- **Token version** (`users.token_version`) is bumped on each login to invalidate other sessions.
- **All DB access goes through repository classes** — no raw SQLAlchemy in route handlers.

## Environment variables (`.env` in `apps/backend/`)

| Variable                      | Default              | Description                                    |
|-------------------------------|----------------------|------------------------------------------------|
| `debug`                       | `false`              | SQLAlchemy echo + debug logging                |
| `languages`                   | `[]`                 | Extra Stanza pipelines to preload at startup   |
| `use_gpu`                     | `false`              | CUDA for Stanza                                |
| `model_dir`                   | `stanza_resources`   | Stanza model cache path                        |
| `storage_root`                | `/app/storage`       | Root for all uploaded files                    |
| `db_host`                     | `localhost`          | PostgreSQL host                                |
| `db_port`                     | `5432`               | PostgreSQL port                                |
| `db_database`                 | `db`                 | DB name                                        |
| `db_username`                 | `user`               | DB user                                        |
| `db_password`                 | `password`           | DB password                                    |
| `redis_url`                   | `redis://redis:6379` | ARQ + general Redis                            |
| `jwt_secret`                  | —                    | JWT signing secret **(required)**              |
| `db_encryption_key`           | —                    | AES-256 key for encrypted API keys **(required)** |
| `max_upload_bytes`            | `524288000` (500 MB) | Upload size limit                              |
| `access_token_expire_minutes` | `60`                 | Access JWT TTL                                 |
| `refresh_token_expire_days`   | `31`                 | Refresh token TTL                              |
| `deepl_api_key`               | —                    | DeepL API key (optional, system-wide fallback) |
| `openai_api_key`              | —                    | OpenAI API key (optional)                      |
| `openai_model`                | `gpt-5.4-mini`       | OpenAI model for grammar/synonyms              |
| `claude_api_key`              | —                    | Claude API key (optional)                      |
| `claude_model`                | `claude-sonnet-4-6`  | Claude model for grammar/synonyms              |
| `admin_email`                 | —                    | Auto-create first admin on startup             |
| `admin_password`              | —                    | Auto-create first admin on startup             |
| `qwen_tts_url`                | —                    | Qwen TTS endpoint (optional)                   |
| `qwen_tts_api_key`            | —                    | Qwen TTS API key (optional)                    |

<!-- MEMORY:START -->
# cafe-backend

_Last updated: 2026-04-15 | 0 active memories, 0 total_

_For deeper context, use memory_search, memory_related, or memory_ask tools._
<!-- MEMORY:END -->
