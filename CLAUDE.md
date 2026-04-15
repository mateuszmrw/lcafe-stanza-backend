# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project: Slovo

Self-hosted language learning platform (LingQ-clone). Users upload EPUB/PDF books, YouTube videos, or website articles. The backend tokenizes content with Stanza NLP, and the reader lets them look up words, track vocabulary statuses, get translations, grammar explanations, and synonym nuance. Includes EPUB3 audiobook support (SMIL overlays), YouTube video sync with subtitles, on-demand TTS generation, website article import (trafilatura), reading streaks, Anki sync, and word frequency coverage stats.

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
ARQ worker — tokenize_page, align_smil_audio, generate_tts_audio, import_youtube_subtitles
    ↓ Stanza NLP / Qwen TTS / yt-dlp / trafilatura
Browser (SSE for real-time import + audio alignment progress)
```

**Content types:**
- **Books** — EPUB/PDF upload → chunk → tokenize → paginated reader
- **YouTube** — yt-dlp subtitle fetch → chunk → tokenize → video-synced continuous scroll reader (ADR-010, ADR-011)
- **Website** — trafilatura article extraction → chunk → tokenize → paginated reader (no chapters sidebar)

**External services:**
- DeepL API — translation (multi-instance: multiple source→target pairs in `deepl_instances` table)
- Wiktionary + OpenRussian + CC-CEDICT + dict.cc + KRDict — dictionary lookups (pre-imported via admin)
- OpenAI / Claude — grammar explanation and synonym nuance (LLM cascade: DB system key → env var)
- Qwen TTS — text-to-speech generation for books without embedded audio
- YouTube (yt-dlp) — video metadata + subtitle extraction

## Critical design decisions

Read `.claude/ClaudeReference.md` before making structural decisions. The non-negotiable rules:

- **Vocabulary keyed by lemma** (since migration 0042). `words.word` stores `token.l.lower().strip()`. `content_pages.lemma_map` (JSONB) maps `{surface → lemma}` for read-time enrichment. Frontend sends `token.l` for status changes. Pre-0042 pages (lemma_map=null) fall back to surface-form lookup.
- **StanzaClient is a singleton** — initialized once at startup, never per-request. Current processors: `tokenize,pos,lemma,depparse`. Token output includes `dep_head` and `dep_rel` (shown as "Role in sentence" in the reader).
- **Redis lives in `app.state`** — created in `lifespan`, accessed via `get_redis(request)` and `get_arq_pool(request)` dependencies.
- **API keys are AES-256 encrypted** in the DB using `db_encryption_key`. Never store plaintext.
- **Token version** (`users.token_version`) is bumped on each login to invalidate other sessions.
- **All DB access goes through repository classes** — no raw SQLAlchemy in route handlers.
- **ContentItem is polymorphic** — `type` field: `"book"`, `"youtube"`, `"website"`. `list_books()` filters all three. YouTube has `youtube_videos` join table; websites use `source_url` column on `content_items`.
- **YouTube time-index sync** (ADR-011) — `GET /books/{id}/time-index` returns flat sorted array of all sentence alignments. Frontend loads once, binary search on tick for O(log N) page + sentence lookup. Page changes debounced (2 consecutive ticks).
- **Anki sync uses custom "Slovo" model** — 10-field note model (Word, POS, Gender, Reading, Morphology, Definition, Hint, SentenceContext, FrequencyTier, Audio). Auto-created via AnkiConnect. Deck naming: `{username}::{LanguageName}`. Audio clips from EPUB audiobooks via ffmpeg at sync time. Dictionary definitions and frequency tiers batch-fetched. Words track `source_page_id` + `source_sentence_index` (since migration 0051) for audio lookup.
- **Book coverage preview** — library cards show "You know X%" for completed books. `CoverageService` computes per-book coverage (unique lemmas from `lemma_map` vs user's known/learning/well_known vocab). Redis-cached 5 min, invalidated alongside stats cache on vocabulary mutations.
- **Word difficulty scoring** — per-word score 0-100 combining frequency rank (0.3), inflection form count (0.3), and personal lookup/exposure ratio (0.4). Stored on `words.difficulty_score`, recomputed on page engagement + word lookup. Minimum 3 exposures before scoring. Reader tokens vary color intensity by difficulty. Vocabulary list has difficulty column with color-coded badges.
- **Grammar annotation** — phrase/selection view in DefinitionPanel shows table of tokens with dep_rel color + role label + case. Localized labels (en/ru/de/pl). `saved_sentences.tokens` JSONB stores annotation at save time. Word view shows grammar on a separate tab (not inline).
- **DefinitionPanel UX** — word mode uses 3 tabs (LingQ-style): Info (status + translation + synonyms), Grammar (case, mood, dep_rel, feats), Dictionary (definitions + forms). On mobile/tablet: floating popup near the tapped word (~55% viewport height, dismissible via backdrop). On desktop: inline side panel. NLP feats filtered to useful subset (Number, Tense, Aspect, Voice only).
- **Reader "Finish" button** — last page shows "Finish" instead of disabled "Next". Auto-advances words, records activity, invalidates coverage cache, navigates to library.

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
