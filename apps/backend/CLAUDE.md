# CLAUDE.md — Backend

FastAPI + Stanza NLP + ARQ worker service for Slovo.

## Source layout

```
src/
  main.py                          # App factory — lifespan, middleware, _register_routes()
  core/
    config.py                      # Settings (pydantic-settings, @lru_cache)
  api/
    dependencies.py                # FastAPI DI: get_db, get_current_user, require_admin,
                                   #   get_nlp_adapter, get_tokenizer, get_redis, get_arq_pool
    routes/
      auth.py                      # POST /auth/{register,login,refresh,logout}
      users.py                     # GET/PATCH /users/me + /me/proficiency + /me/api-keys + /me/data
      books.py                     # CRUD + upload + SSE + audio streaming for books/pages
      vocabulary.py                # GET/PUT/PATCH/POST /vocabulary + Anki sync
      translation.py               # POST /translate (multi-instance DeepL fan-out)
      dictionary.py                # GET /dictionary (Wiktionary lookup + frequency tier)
      languages.py                 # GET /languages
      grammar.py                   # POST /grammar/explain (LLM, rate-limited 3/min)
      synonyms.py                  # POST /synonyms/nuance (LLM, rate-limited 10/min)
      phrases.py                   # CRUD /phrases
      sentences.py                 # CRUD /sentences (saved sentences from reader)
      activity.py                  # POST /activity/record, GET /activity/streak + /calendar
      stats.py                     # GET /stats/{language_code} (Redis-cached 5 min)
      nlp.py                       # POST /nlp/tokenize (legacy, synchronous)
      stanza.py                    # GET/POST /models (install/list/remove Stanza models)
      content.py                   # POST /import/{text,website,book} (preview import)
      setup.py                     # POST /setup (first-run admin creation)
      health.py                    # GET /health
      admin/
        languages.py               # CRUD /admin/languages + NLP config
        providers.py               # CRUD /admin/providers
        users.py                   # GET/PATCH/DELETE /admin/users
        dictionary.py              # POST /admin/dictionary (Wiktionary import)
        frequencies.py             # POST /admin/frequencies (CSV word frequency import)
        system_keys.py             # CRUD /admin/system-keys (encrypted API keys)
        deepl_instances.py         # CRUD /admin/deepl-instances
        llm.py                     # GET/PUT /admin/llm (OpenAI / Claude config)
        anki.py                    # GET/PUT /admin/anki (AnkiConnect URL)
        tts.py                     # POST /admin/tts/test (Qwen TTS test)
        data.py                    # DELETE /admin/data/reset (requires "DELETE ALL DATA")
    schemas/
      auth.py, books.py, users.py, vocabulary.py, admin.py, grammar.py, audio.py
    middleware/
      __init__.py                  # setup_cors (wildcard), setup_error_handling, setup_logging
      error_handling.py            # ErrorHandlingMiddleware — catch-all 500
      logging_middleware.py        # Request/response logging
  domain/
    auth/services/
      jwt.py                       # create_access_token, create_refresh_token, decode_token
                                   #   Algorithm hardcoded to HS256 (_ALGORITHM constant)
      password.py                  # hash_password, verify_password (bcrypt)
    content/
      service.py                   # ContentService — book import orchestration
      page_enricher.py             # collect_surface_forms, enrich_page_tokens
    grammar/service.py             # GrammarExplanationService — LLM prompt + JSON parse
    nlp/
      models/token.py              # Token dataclass
      services/
        tokenizer.py               # Tokenizer (wraps NlpPort, used by legacy /nlp route)
        book_parser.py             # EPUB → chapters; detect_smil_overlays()
        pdf_parser.py              # PDF → chapters
        text_parser.py             # Plain text → sentence-bounded pages
        book_chunker.py            # Chapters → Chunk list (max ~3000 chars, sentence-aligned)
    audio/
      smil_parser.py               # Parse EPUB3 SMIL manifests → Fragment list
      extractor.py                 # Extract embedded audio from EPUB to disk
      fragment_resolver.py         # Map SMIL fragments to (page_id, sentence_index)
    ports/nlp_port.py              # NlpPort abstract interface
    rate_limit.py                  # check_rate_limit(redis, key, limit, window_seconds)
    stats/cache.py                 # invalidate_stats_cache(redis, user_id)
    users/
      models.py                    # UserCreate, UserUpdate Pydantic models
      service.py                   # UserService — register, update, deactivate
  infrastructure/
    db/
      engine.py                    # Async engine + AsyncSessionFactory
      models/
        users.py                   # User, UserLanguageProfile
        content.py                 # ContentItem, Book, ContentPage
        words.py                   # Word (vocabulary)
        languages.py               # Language, LanguageNlpConfig
        providers.py               # Provider
        deepl_instances.py         # DeepLInstance
        system_api_keys.py         # SystemApiKey (encrypted)
        user_api_keys.py           # UserApiKey (encrypted)
        dictionary_entries.py      # DictionaryEntry (Wiktionary)
        word_frequencies.py        # WordFrequency (rank + tier)
        audio.py                   # SentenceAlignment, TtsSentenceCache
        phrases.py                 # Phrase
        sentences.py               # SavedSentence
        activity.py                # DailyActivity
        anki.py                    # AnkiSettings
      repositories/
        word_repo.py               # WordRepository
        content_repo.py            # ContentRepository
        content_page_repo.py       # ContentPageRepository
        user_repo.py               # UserRepository (incl. list_all)
        user_language_profile_repo.py  # UserLanguageProfileRepository (incl. upsert)
        deepl_instance_repo.py     # DeepLInstanceRepository
        language_repo.py           # LanguageRepository
        provider_repo.py           # ProviderRepository
        api_key_repo.py            # ApiKeyRepository (AES-256 encrypt/decrypt)
        system_api_key_repo.py     # SystemApiKeyRepository (AES-256)
        dictionary_repo.py         # DictionaryEntryRepository
        word_freq_repo.py          # WordFrequencyRepository
        audio_repo.py              # AudioRepository (sentence alignments)
        phrase_repo.py             # PhraseRepository
        sentences_repo.py          # SavedSentenceRepository
        activity_repo.py           # DailyActivityRepository
        anki_repo.py               # AnkiRepository (learning/pending words + settings)
    stanza/
      client.py                    # StanzaClient singleton — get_stanza_client()
      adapter.py                   # StanzaNlpAdapter (NlpPort impl)
    deepl/client.py                # DeepL HTTP client
    wiktionary/db_adapter.py       # Dictionary lookup from DictionaryEntry table
    llm/
      client.py                    # Abstract LLM base + OpenAIClient + ClaudeClient
      resolver.py                  # resolve_llm_client(session) — DB key → env var cascade
    tts/providers/qwen.py          # Qwen TTS HTTP client
  worker/
    settings.py                    # ARQ WorkerSettings — registers all tasks
    events.py                      # publish_import_event → Redis pub/sub
    tasks/
      tokenize_page.py             # Tokenize page text, upsert words, finalize book
      align_smil_audio.py          # Parse SMIL, extract audio, build sentence alignments
      generate_tts_audio.py        # Generate DASH TTS audio per page
```

## Auth pattern

- JWT HS256. `get_current_user` decodes Bearer token, checks `token_version` against DB, loads `User`.
- `require_admin` depends on `get_current_user` and checks `user.role == "admin"`.
- Refresh tokens are hashed (SHA256) and stored in `users.refresh_token_hash`. On refresh, hash is verified.
- Login bumps `user.token_version` — invalidates all other active sessions immediately.
- `_ALGORITHM = "HS256"` is a module constant in `jwt.py` — not configurable via env.

## Database access pattern

- **Always use repositories** for DB access from routes. No raw SQLAlchemy in route handlers.
- Repositories are stateless — instantiate as module-level singletons: `_word_repo = WordRepository()`.
- `AsyncSession` is injected via `get_db()` (yields one session per request).
- Mutations: routes call `await session.commit()` explicitly. Workers use `AsyncSessionFactory` as async context manager.

## Vocabulary / word key rules

- Words are stored by **lemma** (`token.l.lower().strip()`) since migration 0042. The `word` column stores the lemma value.
- Unique constraint: `(user_id, language_id, word)` — same index, now keyed by lemma.
- `content_pages.lemma_map` (JSONB, nullable) holds `{surface_form: lemma}` built at tokenization time.
- `get_pages` translates surface forms → lemmas via `page.lemma_map` before querying `words` table.
- `enrich_page_tokens` accepts `lemma_map` param; falls back to surface form for pre-0042 pages (null map).
- PostgreSQL `INSERT … ON CONFLICT DO UPDATE` for all upserts (single round-trip).
- Frontend must send `token.l` (lemma) for status changes — **never `token.w`** (surface form).

## Stanza pipeline

- `StanzaClient` is a global singleton initialized at startup via `get_stanza_client()`.
- Current processors: `tokenize,pos,lemma`. Adding `depparse` costs ~300ms latency + ~15% memory per language.
- `tokenize_sync(lang, text)` → `list[dict]` with keys: `w, l, pos, r, g, feats, pi, si, dep_head, dep_rel`.
- `feats` is Stanza's raw morphological string, e.g. `"Case=Nom|Gender=Masc|Number=Sing"`.
- Workers call `stanza_client.tokenize_sync()` inside `asyncio.to_thread()` (CPU-bound, not async-friendly).

## Redis / lifespan

- Redis and ARQ pool are created in the `lifespan` context manager in `main.py` and stored on `app.state`.
- **Never** create Redis connections outside lifespan. Access via:
  - `get_redis(request: Request)` → `request.app.state.redis`
  - `get_arq_pool(request: Request)` → `request.app.state.arq`
- On shutdown, both connections are properly closed.

## Worker (ARQ)

### `tokenize_page(ctx, page_id)`
- Dispatched by `upload_book` — one job per page.
- Calls `_load_page_context` → `_resolve_auto_ignore` → `_build_word_rows` → `bulk_upsert` → mark page `"ready"`.
- Updates Redis progress counters: `book:{book_id}:completed_pages`, `book:{book_id}:token_count`.
- Publishes SSE progress to Redis channel `import:{book_id}`.
- On completion (SETNX finalization lock): sets `content_item.status = "completed"`, publishes `"completed"` event.
  If `book.has_audio_overlay`, enqueues `align_smil_audio`.

### `align_smil_audio(ctx, book_id)`
- Triggered by `tokenize_page` finalization (EPUB3 with SMIL overlays) or directly by retrigger endpoint.
- Parses SMIL manifests, extracts audio to `storage_root/books/{book_id}/audio/`.
- Matches SMIL fragments to page sentences → inserts into `sentence_alignments` table.
- Sets `book.audio_file_path`, publishes progress + `"complete"` SSE event.

### `generate_tts_audio(ctx, book_id)`
- Triggered by `POST /books/{id}/audio/generate-tts`.
- Calls Qwen TTS per sentence (with `TtsSentenceCache` deduplication by `text_hash`).
- Generates DASH manifest (.mpd + .m4s segments) per page → stores in `storage_root/books/{book_id}/tts/`.
- Updates `content_page.tts_manifest_path`, sets `book.tts_status = "complete"`.

## DeepL multi-instance

- `deepl_instances` table stores enabled (source_lang, target_lang) pairs.
- `POST /translate` queries all enabled instances for the given `source_lang`, fires parallel DeepL requests (one per target language), returns all results.
- API key resolution order: user DB key → system DB key → `deepl_api_key` env var.

## LLM provider cascade

Used by grammar explanation and synonym nuance:
1. Query `system_api_keys` for OpenAI key → if found, use `OpenAIClient`.
2. Fall back to `openai_api_key` env var.
3. Query `system_api_keys` for Claude key → if found, use `ClaudeClient`.
4. Fall back to `claude_api_key` env var.
5. If nothing found, raise HTTP 503.

Shared via `resolve_llm_client(session)` in `infrastructure/llm/resolver.py`.

## Grammar explanation

**Endpoint:** `POST /grammar/explain` (rate-limited: 3 req/min/user)

Frontend sends pre-tokenized tokens — no re-tokenization at request time. Route checks:
1. User has `active_language_id` set.
2. `UserLanguageProfile.proficiency_level` (A1–C2) is set for that language.
3. Rate limit not exceeded.

LLM receives token morphology + proficiency level. Output: token annotations + prose explanation in learner's native language.

## Synonym nuance

**Endpoint:** `POST /synonyms/nuance` (rate-limited: 10 req/min/user)

LLM finds 2–4 near-synonyms with register classification (formal/informal/slang/etc.) and nuance explanation. All explanations in learner's native language.

## Auto-ignore proper nouns

Worker reads effective setting (per-language profile → global user setting) before building word rows.
Words with `pos == "PROPN"` get `status = "ignored"` if the setting is true.

## Admin data reset

- `DELETE /admin/data/reset` requires body `{"confirmation": "DELETE ALL DATA"}`.
- Deletes all `words` + `content_items` (cascades to `books`, `content_pages`, `phrases`, `saved_sentences`).
- Wipes `storage_root/books/` on disk.

## Pyright false positives

IDE shows `reportMissingImports` for `fastapi`, `sqlalchemy`, etc. — the venv is not configured for the IDE. These are not real errors. Run `uv run mypy src` for actual type checking.

<!-- MEMORY:START -->
# backend

_Last updated: 2026-04-15 | 0 active memories, 0 total_

_For deeper context, use memory_search, memory_related, or memory_ask tools._
<!-- MEMORY:END -->
