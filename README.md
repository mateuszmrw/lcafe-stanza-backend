# Slovo

**Self-hosted language-learning reader. Upload books, YouTube videos, or web articles in your target language; the backend tokenizes them with real NLP, and the reader lets you look up words, track what you know, and grow your vocabulary as you read.**

Think LingQ / Readlang / LWT — but on your own hardware, with your data, no subscription, and open source.

This is a personal project. I'm not looking for users or contributors and I won't be promoting it or providing support. If you find it useful, feel free to run it. The code is here; that's all.

## Use these instead

Slovo is heavily inspired by two excellent, actively maintained, community-supported projects. If you're looking for a self-hosted LingQ-style reader you can actually rely on, use one of these — they're more polished, better tested, and have real communities behind them:

- **[LinguaCafe](https://github.com/simjanos-dev/LinguaCafe)** — full-featured, polished UI, active community, broad language coverage.
- **[Lute (v3)](https://github.com/LuteOrg/lute-v3)** — mature LWT descendant, lightweight, well-documented, great for extensive reading.

I built Slovo to scratch my own itch (lemma-keyed vocab, Stanza dependency parsing, EPUB3 SMIL audio, YouTube sync, Anki export with the shape *I* want). It's not a replacement for those tools — it's a personal fork of the idea. Go use LinguaCafe or Lute.

---

## Features

**Content import**

- **EPUB + PDF books** — full book import, chapter sidebar, paginated reader, per-page progress
- **EPUB3 audiobooks** — SMIL overlays are parsed and sentence-aligned to the audio; tap a sentence to jump to it, karaoke-style highlighting during playback
- **YouTube videos** — `yt-dlp` fetches subtitles (manual or auto), the reader syncs the text with the video as you watch
- **Website articles** — paste a URL, `trafilatura` extracts the text, reader opens on a clean paginated view
- **On-demand TTS** — for books without embedded audio, generate speech per sentence via any OpenAI-compatible TTS backend

**Reader**

- **Click any word** for definition, translation, grammar breakdown, and near-synonyms
- **Phrase selection** — drag to select, get a translation and grammar annotation for the full phrase
- **Vocabulary statuses**: New → Learning → Known → Well-known, plus Ignored. Keyboard shortcuts `1`-`5`
- **Page navigation**: keyboard (`J`/`K` or arrow keys), audio-driven auto-advance, or buttons
- **Difficulty-aware rendering** — each word's colour intensity scales with a 0–100 difficulty score computed from frequency rank, inflection complexity, and your personal lookup/exposure ratio
- **Reader settings**: font size, line spacing, text width, all per-user

**Vocabulary & progress**

- **Vocabulary keyed by lemma** — so `бежит`, `бегу`, `бежал` all count as one Russian word (`бежать`)
- **Book coverage preview** — library cards show "you know X%, mastered Y%" for each completed book as a two-tone bar
- **Word frequency coverage stats** — per-language dashboard, based on frequency lists you import as admin
- **Reading streaks + calendar heatmap** (past-year view)
- **Anki sync** — one-click export to Anki via AnkiConnect, with a 10-field "Slovo" note model including audio clips extracted from EPUB audiobooks

**Dictionaries, translation, LLM**

- **Dictionary lookup** — Wiktionary + OpenRussian + CC-CEDICT + dict.cc + KRDict. All pre-imported by admin (one-time setup), no per-request API calls
- **Translation** — DeepL API, multi-instance (configure several source→target pairs, all fire in parallel)
- **Grammar explanations** — OpenAI (your key), proficiency-aware, rate-limited
- **Synonym nuance** — near-synonyms with register classification (formal / informal / slang / etc.) and explanations in your native language

**Self-host friendly**

- One `docker compose up` gets Postgres + Redis + backend + ARQ worker + frontend running
- No mandatory cloud services; every external integration (DeepL, OpenAI, TTS) is optional
- No telemetry, no analytics, no phone-home
- Admin UI for configuring languages, API keys, dictionaries, and frequency imports

**Languages**: anything Stanford [Stanza](https://stanfordnlp.github.io/stanza/) supports (70+). Pre-tested with Russian, Polish, English. Models are auto-downloaded on first use.

---

## Quick start (Docker Compose)

Requirements: Docker + Docker Compose.

```bash
git clone https://github.com/YOUR_USER/slovo.git
cd slovo

# Generate the two required secrets (both must be ≥32 chars)
echo "JWT_SECRET=$(openssl rand -base64 32)" >> .env
echo "DB_ENCRYPTION_KEY=$(openssl rand -base64 32)" >> .env

docker compose up -d
```

- Web UI: http://localhost:4412
- Backend API: http://localhost:8678 (docs at `/docs`)
- Open the web UI and create the first admin account, then go to **Admin → Languages** to enable the languages you want, and **Admin → Dictionary / Frequencies** to import dictionary data.

### Resources

Stanza NLP is CPU and RAM heavy. A modest VPS (2 cores / 4 GB RAM) handles one user with a handful of languages. The ARQ worker and backend each hold their own Stanza pipelines in memory (~500 MB per loaded language). For GPU acceleration, set `USE_GPU=true` and provide a CUDA-capable Docker runtime.
The CUDA or GPU support in general is not tested.

---

## Environment variables

Set these in `.env` at the repo root (the same directory as `docker-compose.yaml`).

### Required

| Variable            | Notes                                                         |
| ------------------- | ------------------------------------------------------------- |
| `JWT_SECRET`        | 32+ chars. Signs access/refresh tokens. Validated at startup. |
| `DB_ENCRYPTION_KEY` | 32+ chars. AES-256 key for encrypted API keys in the DB.      |

Generate both with `openssl rand -base64 32`.

### Database

| Variable      | Default                                |
| ------------- | -------------------------------------- |
| `DB_DATABASE` | `db`                                   |
| `DB_USERNAME` | `user`                                 |
| `DB_PASSWORD` | `password`                             |
| `DB_HOST`     | `postgresql` (service name in Compose) |
| `DB_PORT`     | `5432`                                 |

### Optional integrations

All of these are fully optional — the app runs without them, with the corresponding features disabled.

| Variable             | Purpose                                                                    |
| -------------------- | -------------------------------------------------------------------------- |
| `DEEPL_API_KEY`      | System-wide DeepL fallback (users can also set their own keys via the UI). |
| `OPENAI_API_KEY`     | LLM for grammar explanations & synonym nuance.                             |
| `OPENAI_MODEL`       | Default: `gpt-5.4-mini`.                                                   |
| `OPENAI_TTS_URL`     | Base URL of an OpenAI-compatible TTS server.                               |
| `OPENAI_TTS_API_KEY` | Bearer token for the TTS server.                                           |
| `OPENAI_TTS_MODEL`   | Model id sent to the TTS server.                                           |

### Other

| Variable                      | Default                 | Notes                                                                                  |
| ----------------------------- | ----------------------- | -------------------------------------------------------------------------------------- |
| `LANGUAGES`                   | `[]`                    | JSON list of Stanza language codes to pre-load at startup.                             |
| `USE_GPU`                     | `false`                 | Enable CUDA for Stanza.                                                                |
| `MAX_UPLOAD_BYTES`            | `104857600` (100MB)     | Generic upload cap (SRT subtitles, frequency CSVs).                                    |
| `MAX_BOOK_UPLOAD_BYTES`       | `524288000` (500MB)     | EPUB/PDF upload size cap.                                                              |
| `MAX_DICTIONARY_UPLOAD_BYTES` | `2147483648` (2GB)      | Wiktionary / dictionary dump upload size cap (admin).                                  |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60`                    | Access JWT TTL.                                                                        |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | `31`                    | Refresh token TTL.                                                                     |
| `STORAGE_ROOT`                | `/app/storage`          | Where uploaded files live on disk (Docker volume).                                     |
| `REDIS_URL`                   | `redis://redis:6379`    | ARQ queue + SSE pubsub + rate-limit counters.                                          |
| `NEXT_PUBLIC_API_URL`         | `http://localhost:8678` | Baked into the frontend bundle at Docker build time. Must be reachable by the browser. |

---

## Running from source

```bash
# Backend (FastAPI + Stanza + ARQ worker)
cd apps/backend
uv sync
uv run fastapi dev src/main.py --port 8678
uv run pytest                     # all tests
uv run ruff check src              # lint
uv run mypy src                    # type check
uv run alembic upgrade head        # apply migrations

# Frontend (Next.js 15, App Router)
cd apps/web
pnpm install
pnpm dev                           # dev server on :3000
pnpm lint
```

Tooling:

- **Backend**: Python 3.12, [`uv`](https://docs.astral.sh/uv/), FastAPI, SQLAlchemy (async + asyncpg), ARQ, Stanza, pydantic v2
- **Frontend**: Next.js 15 (App Router), React 19, TypeScript, Zustand, TanStack Query, Tailwind
- **Infra**: PostgreSQL 15, Redis 7

Architecture notes and design decisions live in `docs/adr/` (ADRs) and `docs/architecture/` (C4 Mermaid diagrams).

---

## Project structure

```
apps/
  backend/   FastAPI + Stanza + ARQ worker (Python 3.12, uv)
  web/       Next.js 15 frontend (TypeScript, pnpm)
docs/
  adr/            Architecture Decision Records
  architecture/   C4 diagrams (Mermaid)
```

## License

MIT — see `apps/backend/LICENSE.md`.
