# CLAUDE.md — Frontend

Next.js 15 App Router frontend for Slovo.

## Source layout

```
app/
  layout.tsx                       # Root layout — QueryClientProvider, AuthProvider
  (app)/                           # Authenticated shell (sidebar nav)
    layout.tsx                     # App shell with sidebar
    library/page.tsx               # Book library grid — upload, delete, status
    reader/[id]/page.tsx           # Reader — ?page=N param, progress in localStorage
    vocabulary/page.tsx            # Vocabulary list — filters, export CSV, Anki sync
    phrases/page.tsx               # Saved phrases — status filter, delete
    sentences/page.tsx             # Saved sentences from reader — delete
    stats/page.tsx                 # Word counts, progress chart, frequency coverage
    activity/page.tsx              # Reading streak + calendar heatmap (past year)
    settings/
      profile/page.tsx             # Username, email, native language, proficiency
      api-keys/page.tsx            # Per-provider API key management
      data/page.tsx                # Account deletion + data reset
    admin/
      layout.tsx                   # Admin tab nav (redirects non-admins)
      languages/page.tsx           # Language CRUD
      providers/page.tsx           # Provider CRUD
      dictionary/page.tsx          # Wiktionary import
      frequencies/page.tsx         # Word frequency CSV import
      system-keys/page.tsx         # System-level API key management
      deepl-instances/page.tsx     # DeepL source→target pair management
      llm/page.tsx                 # OpenAI model configuration
      anki/page.tsx                # AnkiConnect URL configuration
      users/page.tsx               # User list — role/active management
      data/page.tsx                # All-data reset (requires "DELETE ALL DATA")
  (auth)/                          # Unauthenticated pages
    login/page.tsx
    register/page.tsx
    setup/page.tsx                 # First-run admin creation

src/
  lib/
    api/
      client.ts                    # apiClient() + apiUpload() — auth, 401 refresh+retry
      books.ts                     # getBook, getBookPages, uploadBook, deleteBook,
                                   #   getPageAlignments, generateTts, getTtsStatus
      vocabulary.ts                # listVocabulary, upsertWordStatus, batchUpsertWordStatus,
                                   #   bulkUpdateStatus, exportVocabulary, syncAnki
      translation.ts               # translate(), getTranslationAvailable()
      dictionary.ts                # lookup() → DictionaryEntry[] + FrequencyInfo
      languages.ts                 # listLanguages()
      grammar.ts                   # explainGrammar() → GrammarExplainResponse
      synonyms.ts                  # getSynonymNuance() → SynonymNuanceResponse
      phrases.ts                   # createPhrase, listPhrases, updatePhrase, deletePhrase
      sentences.ts                 # saveSentence, listSentences, deleteSentence
      activity.ts                  # recordActivity, getStreak, getCalendar
      stats.ts                     # getStats(languageCode) → StatsResponse
      admin-*.ts                   # Admin API modules (languages, users, keys, etc.)
    status-colors.ts               # STATUS_CLASSES + STATUSES + getTokenClass(status, difficulty)
    grammar.ts                     # dep_rel colors/labels (localized), feats parser, SentenceToken type
    tokens.ts                      # getLemmaKey(token) — USE THIS instead of `t.l || t.w`
    search.ts                      # upperBoundBy() — reusable binary search (used by audioPlayer)
    language-flags.ts              # LANGUAGE_FLAGS + getLanguageLabel()
    reading-progress.ts            # getReadingProgress / saveReadingProgress / saveAudioProgress (localStorage)
    cn.ts                          # clsx + tailwind-merge helper
  stores/
    auth.ts                        # Zustand: user, accessToken, login, logout, setActiveLanguage
    reader.ts                      # Zustand: activeToken, selectedText, setActiveToken,
                                   #   setSelectedText, clearActive
  components/
    reader/
      ReadingPane.tsx              # Page content, pagination, drag-select tokens
      WordToken.tsx                # Single token <span> — status color from status-colors.ts
      DefinitionPanel.tsx          # Right panel: NLP info, status buttons, translation,
                                   #   dictionary, grammar, synonyms. Also: selection mode.
      ChapterSidebar.tsx           # Left chapter list with page counts
      AudioPlayer.tsx              # SMIL/TTS audio player with sentence highlighting
    ui/                            # Shared: Badge, Button, Input, Dialog, etc.
```

## Key data flow — reader

1. `reader/[id]/page.tsx` — holds current `page` (URL `?page=N`), fetches book metadata.
2. `ReadingPane` — fetches `getBookPages(bookId, page, 1)` via TanStack Query. Renders tokens as flat list (paragraph/sentence indexed). Implements drag selection.
3. `WordToken` — `<span role="button">`. Click → sets `activeToken` in Zustand. Mouse drag → sets `selectedText` in Zustand. Status color from `STATUS_CLASSES` in `status-colors.ts`.
4. `DefinitionPanel` — shown when `activeToken !== null`. Word mode: NLP metadata + status buttons + translation + dictionary + grammar + synonyms. Selection mode (when `selectedText` set): translation only.
5. Status change — `upsertWordStatus(token.w, ...)` → patches TanStack Query cache via `setQueriesData` (instant feedback, no refetch).
6. Page turn (`setPage`) — auto-advances all "new" tokens to "well_known", saves progress to localStorage, navigates via `router.replace`.
7. Audio — `AudioPlayer` reads `SentenceAlignment` data to highlight current sentence during playback. Supports SMIL-extracted audio and DASH TTS segments.

## TokenWithStatus shape

```ts
interface TokenWithStatus {
  id?: string      // Word DB UUID (undefined if not yet in vocabulary)
  w: string        // Surface form (displayed in reader)
  l: string        // Lemma
  pos: string      // Universal POS tag (NOUN, VERB, PUNCT…)
  r: string        // Reading (CJK furigana/pinyin)
  pi: number       // Paragraph index within page
  si: number       // Sentence index within page (global, 0-based)
  g: string        // Grammatical gender
  f: string        // Raw feats string e.g. "Case=Nom|Gender=Masc|Number=Sing"
  dep_head: number // Dependency head token index
  dep_rel: string  // Dependency relation label
  hint?: string    // User note
  status: "new" | "learning" | "known" | "ignored" | "well_known"
  d?: number       // Difficulty score 0-100 (null if < 3 exposures)
}
```

## Vocabulary keys

Always use `token.l` (lemma) for vocabulary upserts — **not** `token.w` (surface form). Since migration 0042, the backend stores words by lemma. Use **`getLemmaKey(token)`** from `src/lib/tokens.ts` instead of writing `t.l || t.w` inline — single source of truth that also applies lowercasing consistently.

## Status colors

`STATUS_CLASSES`, `STATUSES`, and `getTokenClass(status, difficulty)` live in `src/lib/status-colors.ts` — single source of truth. `WordToken` uses `getTokenClass` which scales opacity by difficulty score. Do not redefine these locally.

## TanStack Query conventions

- Query keys: `["book", id]`, `["book-pages", bookId, page]`, `["vocabulary", languageId, ...]`, `["languages"]`, `["stats", languageCode]`.
- After status mutations, patch the cache with `queryClient.setQueriesData<PageListResponse>({ queryKey: ["book-pages"] }, ...)` — no round-trip refetch.
- Book page queries: `placeholderData: (prev) => prev` to prevent flash on page change.
- Import polling: `refetchInterval: (query) => query.state.data?.items[0]?.status === "pending" ? 3000 : false`.

## API client

- `apiClient<T>(path, options)` — adds `Authorization: Bearer {token}`, handles 401 refresh+retry, redirects to `/login` if refresh fails.
- `apiUpload<T>(path, formData)` — same 401 refresh+retry logic as `apiClient`. Skips `Content-Type` so browser sets multipart boundary.
- Both retry exactly once after a successful token refresh — no infinite loops.

## Auth

- Zustand `auth` store holds both the access token and refresh token in memory.
- `apiClient` reads the access token for every request (`Authorization: Bearer {token}`).
- Refresh token is sent in the **request body** as JSON to `POST /auth/refresh` — not a cookie.
- `useAuth()` from `src/stores/auth.ts`.
- Admin check: `user.role === "admin"` (the `is_admin` derived property).

## Reader store (Zustand)

```ts
setActiveToken(token)           // sets activeToken, clears selectedText
setSelectedText(text, tokens?)  // sets selectedText + selectedTokens; activeToken remains
setSentenceContext(text, tokens?) // sets sentenceContext + sentenceTokens (for grammar annotation)
clearActive()                   // clears all
```

### Zustand selector pattern (performance-critical)

The `audioPlayer` store fires `tick(ms)` at ~5x/sec during playback. Components that
consume it **must use per-field selectors** to avoid re-rendering on every tick:

```ts
// ❌ DON'T — re-renders on every currentTimeMs update
const { activeSentenceIndex, seekToSentence } = useAudioPlayerStore()

// ✅ DO — only re-renders when the specific slice changes
const activeSentenceIndex = useAudioPlayerStore((s) => s.activeSentenceIndex)
const seekToSentence = useAudioPlayerStore((s) => s.seekToSentence)
```

This applies to `ReadingPane`, `KaraokeView`, `SentenceView`, and any new reader component.

## Reading progress

- Stored in localStorage: `"slovo-reading-progress"` → `{[bookId]: pageNumber}`.
- Restored on mount only when no explicit `?page=` URL param.
- Updated on every `setPage()` call.

## Auto-advance "new" words

On page turn:
1. Read current page tokens from TanStack Query cache.
2. Filter `status === "new"`, deduplicate by lowercase surface form.
3. Call `batchUpsertWordStatus(items)` fire-and-forget (errors swallowed so navigation is never blocked).

## Proficiency + per-language settings

- Set via `PATCH /users/me/proficiency` — writes to `UserLanguageProfile` for the active language.
- Fields: `proficiency_level` (A1–C2), `native_language_code`, `auto_ignore_proper_nouns`.
- Grammar explanation requires proficiency to be set; returns 400 otherwise.
- `UserResponse` includes both global and per-language fields with fallback logic.

## Admin — data reset

- `admin/data/page.tsx` confirmation input requires exact text `"DELETE ALL DATA"`.
- Calls `DELETE /admin/data/reset`. Shows deleted book + word counts on success.

<!-- MEMORY:START -->
# web

_Last updated: 2026-04-21 | 0 active memories, 0 total_

_For deeper context, use memory_search, memory_related, or memory_ask tools._
<!-- MEMORY:END -->
