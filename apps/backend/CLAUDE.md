# CLAUDE.md — Backend

FastAPI + Stanza NLP + ARQ worker service for Slovo.

## Source layout

```
src/
  main.py                        # App factory — registers all routers + middleware
  core/
    config.py                    # Settings (pydantic-settings, @lru_cache)
  api/
    dependencies.py              # FastAPI DI: get_db, get_current_user, require_admin,
                                 #   get_nlp_adapter, get_tokenizer, get_arq_pool
    routes/
      auth.py                    # POST /auth/login, /auth/refresh, /auth/logout
      users.py                   # GET/PATCH /users/me
      books.py                   # CRUD + upload + SSE progress for books/pages
      vocabulary.py              # GET/PUT/PATCH/POST /vocabulary + /vocabulary/batch
      translation.py             # POST /translation/translate (multi-instance DeepL)
      dictionary.py              # GET /dictionary/lookup
      languages.py               # GET /languages
      nlp.py                     # POST /nlp/tokenize (legacy)
      setup.py                   # POST /setup (first-run admin creation)
      admin/
        languages.py             # CRUD /admin/languages + NLP config
        providers.py             # CRUD /admin/providers
        users.py                 # GET/PATCH /admin/users
        dictionary.py            # POST /admin/dictionary/import
        system_keys.py           # CRUD /admin/system-keys
        deepl_instances.py       # CRUD /admin/deepl-instances
        data.py                  # DELETE /admin/data/reset (requires "DELETE ALL DATA")
    schemas/
      auth.py, books.py, users.py, vocabulary.py, admin.py
    middleware/                  # CORS, error handling, request logging
  domain/
    auth/services/jwt.py         # JWT encode/decode
    nlp/
      models/token.py            # Token dataclass
      services/tokenizer.py      # Tokenizer (wraps NlpPort)
      services/book_parser.py    # EPUB → chapters
      services/text_parser.py    # Text → sentence-bounded pages
      services/book_chunker.py   # Orchestrates parse → chunk pipeline
    content/service.py           # ContentService — creates ContentItem + Book rows
    ports/nlp_port.py            # NlpPort abstract interface
    users/                       # Minimal user domain
  infrastructure/
    db/
      engine.py                  # SQLAlchemy async engine + AsyncSessionFactory
      models/
        users.py                 # User (id, email, username, role, active_language_id)
        content.py               # ContentItem, Book, ContentPage
        words.py                 # Word (user/language/word unique; feats, status, pos…)
        languages.py             # Language, LanguageNlpConfig
        providers.py             # Provider (stanza slug)
        deepl_instances.py       # DeepLInstance (source_lang, target_lang, enabled)
        system_api_keys.py       # SystemApiKey
        user_api_keys.py         # UserApiKey
        dictionary_entries.py    # DictionaryEntry
      repositories/
        word_repo.py             # WordRepository — bulk_upsert, get_words_map,
                                 #   list_paginated, upsert_with_status, batch_upsert_status
        content_repo.py          # ContentRepository
        deepl_instance_repo.py   # DeepLInstanceRepository
    stanza/
      client.py                  # StanzaClient singleton — get_stanza_client()
      adapter.py                 # StanzaNlpAdapter (NlpPort impl)
    deepl/                       # DeepL HTTP client
    wiktionary/                  # Wiktionary scraper
  worker/
    settings.py                  # ARQ WorkerSettings — registers tokenize_page task
    events.py                    # publish_import_event → Redis SSE pub/sub
    tasks/
      tokenize_page.py           # Core worker task — tokenize page, upsert words,
                                 #   track progress, finalize book on last page
```

## Auth pattern

- JWT Bearer tokens. `get_current_user` verifies token, loads `User` from DB.
- `require_admin` depends on `get_current_user` and checks `user.role == "admin"`.
- Refresh tokens are hashed and stored in `users.refresh_token_hash`.

## Database access pattern

- **Always use repositories** for DB access from route handlers. Never query SQLAlchemy models directly in routes.
- All repositories take `AsyncSession` as first argument (injected via `get_db`).
- `WordRepository` is instantiated as a module-level singleton `_word_repo = WordRepository()` inside route files — this is intentional (stateless).
- Transactions: routes call `await session.commit()` explicitly after mutations. Workers use `AsyncSessionFactory` as an async context manager.

## Vocabulary / word key rules

- Words are stored by **surface form** (`word.lower().strip()`), not lemma.
- The unique index is `(user_id, language_id, word)`.
- `batch_upsert_status` and `upsert_with_status` use PostgreSQL `INSERT … ON CONFLICT DO UPDATE` — single round-trip upserts.
- When updating status from the frontend, always use `token.w` (surface form) as the key, not `token.l` (lemma).

## Stanza pipeline

- `StanzaClient` loads pipelines at startup. Each language has a `ModelConfig(lang, processors)`.
- Current processors: `tokenize,pos,lemma`. `depparse` will be added for grammar explanation (ADR-001) — when adding, update `model_configs` in `client.py` and be aware of +~300ms latency and +~15% memory per language.
- `tokenize_sync(lang, text)` returns `list[dict]` with keys: `w, l, pos, r, g, feats, pi, si`.
- `feats` is Stanza's raw morphological string, e.g. `"Case=Nom|Gender=Masc|Number=Sing"`.

## Worker (ARQ)

- One task: `tokenize_page(ctx, page_id)`.
- Dispatched by `books.py` via `arq_pool.enqueue_job("tokenize_page", str(page.id))`.
- Progress tracked in Redis with `book:{cid}:total_pages` and `book:{cid}:completed_pages`.
- SSE events are published to Redis channel `book-import:{cid}` and consumed by `GET /books/{id}/events`.
- Finalization (`_finalize`) runs once when `completed >= total` using `SETNX` to prevent race conditions.

## DeepL multi-instance

- `deepl_instances` table stores enabled source→target pairs, all sharing a single API key.
- `POST /translation/translate` takes `{text, source_lang}`, queries all enabled instances for that source, and fires one DeepL request per target language.
- API key resolution: user key → system key → `DEEPL_API_KEY` env var.

## Admin data reset

- `DELETE /admin/data/reset` requires body `{"confirmation": "DELETE ALL DATA"}`.
- Deletes all `words` rows, all `content_items` (cascades to `books` + `content_pages`), and wipes `storage_root/books/` on disk.

## Grammar explanation

**Endpoint:** `POST /grammar/explain`

Frontend sends pre-tokenized sentence data — no Stanza re-tokenization at request time. Route validates proficiency is set, enforces rate limit (3 req/min/user), resolves an LLM client, and calls `GrammarExplanationService`.

**Request:**
```json
{ "language_code": "ru", "tokens": [{"w": "Он", "l": "он", "pos": "PRON", "feats": "Case=Nom|..."}] }
```
**Response:**
```json
{ "token_annotations": [{"w": "Он", "annotation": "nominative pronoun — subject"}], "prose_explanation": "..." }
```

**Proficiency levels:** A1–C2 — set via `PATCH /users/me/proficiency` (body: `{proficiency_level, native_language_code}`).

**LLM provider cascade:** system DB key (admin-configured) → env var. Tries OpenAI first, then Claude. There are no per-user LLM keys — only admins configure LLM access.
- `openai_api_key` / `openai_model` (default `gpt-4o`)
- `claude_api_key` / `claude_model` (default `claude-opus-4-6`)

**Rate limiting:** Redis key `grammar:user:{user_id}`, max 3/min, returns 429 on excess.

**Key files:** `src/api/routes/grammar.py`, `src/domain/grammar/service.py`, `src/infrastructure/llm/`, `src/api/schemas/grammar.py`

**Depparse:** deferred — may add to Stanza pipeline later if C1-C2 explanation quality is insufficient.

## Planned features (see ADRs before implementing)

- **Grammar explanation** (`POST /grammar/explain`) — **implemented** (see Grammar explanation section above). Depparse deferred; may add later for C1-C2 quality.
- **Synonym nuance** (`POST /synonyms/nuance`) — ADR-002: LLM synonym discovery, PostgreSQL tsvector corpus search (GIN index on `content_pages.text`), `synonym_explanations` cache table.

## Pyright false positives

IDE shows `reportMissingImports` for `fastapi`, `sqlalchemy`, etc. — the venv is not configured for the IDE. These are not real errors. Run `uv run mypy src` for actual type checking.

<!-- MEMORY:START -->
# backend

_Last updated: 2026-04-10 | 0 active memories, 0 total_

_For deeper context, use memory_search, memory_related, or memory_ask tools._
<!-- MEMORY:END -->
