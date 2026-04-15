# CLAUDE.md — Frontend

Next.js 15 App Router frontend for Slovo.

## Source layout

```
app/
  layout.tsx                     # Root layout — QueryClientProvider, AuthProvider
  (app)/                         # Authenticated shell (sidebar nav)
    layout.tsx                   # App shell with sidebar
    library/page.tsx             # Book library grid
    reader/[id]/page.tsx         # Reader — URL param ?page=N, reading progress in localStorage
    vocabulary/page.tsx          # Vocabulary list with status filters
    admin/
      layout.tsx                 # Admin tab nav (redirects non-admins)
      languages/page.tsx
      providers/page.tsx
      dictionary/page.tsx
      system-keys/page.tsx
      deepl-instances/page.tsx   # DeepL source→target pair management
      users/page.tsx
      data/page.tsx              # Data reset — requires typing "DELETE ALL DATA"
  (auth)/                        # Unauthenticated pages
    login/page.tsx
    register/page.tsx
    setup/page.tsx               # First-run admin setup

src/
  lib/
    api/
      client.ts                  # apiClient() — base fetch with auth headers + error handling
      books.ts                   # getBook, getBookPages, uploadBook, deleteBook, getBookPages
                                 #   Types: TokenWithStatus, PageResponse, PageListResponse
      vocabulary.ts              # listVocabulary, updateWordStatus, upsertWordStatus,
                                 #   batchUpsertWordStatus
      translation.ts             # translate(text, sourceLang) → TranslationResult[]
      dictionary.ts              # lookupWord
      languages.ts               # listLanguages
      admin-data.ts              # resetAllData(confirmation)
      deepl-instances.ts         # getDeepLInstances, createDeepLInstance, etc.
    language-flags.ts            # LANGUAGE_FLAGS map + getLanguageLabel() for DeepL codes
    reading-progress.ts          # getReadingProgress / saveReadingProgress (localStorage)
    cn.ts                        # clsx + tailwind-merge helper
  stores/
    auth.ts                      # Zustand: user, token, login, logout, setActiveLanguage
    reader.ts                    # Zustand: activeToken, selectedText, setActiveToken,
                                 #   setSelectedText, clearActive
  components/
    reader/
      ReadingPane.tsx            # Page content, pagination, drag-selection of tokens
      WordToken.tsx              # Single token <span> with status color + highlight
      DefinitionPanel.tsx        # Right panel: word NLP info, status buttons, translation,
                                 #   dictionary. Also handles selectedText (multi-word) mode.
      ChapterSidebar.tsx         # Left chapter list
    ui/                          # Shared: Badge, Button, etc.
```

## Key data flow — reader

1. `reader/[id]/page.tsx` — holds `page` (from URL `?page=N`), reads `book` metadata.
2. `ReadingPane` — fetches `getBookPages(bookId, page, 1)` via TanStack Query. Renders `<Paragraphs>` with flat token index for drag selection.
3. `WordToken` — each token is a `<span role="button">`. Click sets `activeToken` in Zustand. Mouse drag sets `selectionRange` state in `ReadingPane` and `selectedText` in Zustand.
4. `DefinitionPanel` — rendered when `activeToken !== null`. Shows NLP metadata + status buttons (word mode) or translation-only (selection mode when `selectedText` is set).
5. Status change — calls `upsertWordStatus(token.w, ...)` then patches TanStack Query cache via `setQueriesData` for instant visual feedback (no round-trip refetch).
6. Page change (`setPage`) — auto-advances all "new" tokens to "well_known" via `batchUpsertWordStatus`, saves reading progress to localStorage, navigates via `router.replace`.

## TokenWithStatus shape

```ts
interface TokenWithStatus {
  id?: string      // Word DB UUID; undefined if not in vocabulary
  w: string        // Surface form (what's displayed)
  l: string        // Lemma
  pos: string      // Universal POS tag (NOUN, VERB, PUNCT…)
  r: string        // Reading (for CJK)
  pi: number       // Paragraph index within page
  si: number       // Sentence index within page (global)
  g: string        // Gender from feats
  f: string        // Raw feats string e.g. "Case=Nom|Gender=Masc|Number=Sing"
  status: "new" | "learning" | "known" | "ignored" | "well_known"
}
```

## Vocabulary keys

Always use `token.w` (surface form) for vocabulary upserts — **not** `token.l` (lemma). The backend stores words by surface form. Using lemma as the key causes status changes to silently miss.

## TanStack Query conventions

- Query keys: `["book", id]`, `["book-pages", bookId, page]`, `["vocabulary", languageId]`, `["languages"]`.
- After status mutations, patch the cache with `queryClient.setQueriesData<PageListResponse>({ queryKey: ["book-pages"] }, ...)` to avoid flicker. Do not use `invalidateQueries` for real-time status feedback.
- Book page queries use `placeholderData: (prev) => prev` to prevent flash on page change.
- Polling: `refetchInterval: (query) => query.state.data?.items[0]?.status === "pending" ? 3000 : false` for pages still being tokenized.

## Auth

- Zustand `auth` store holds JWT access token in memory. `apiClient` reads it for every request.
- Refresh token is an httpOnly cookie (handled by `POST /auth/refresh`).
- `useAuth()` hook from `src/stores/auth.ts`.
- Admin check: `user.is_admin` (derived from `user.role === "admin"`).

## Reader store (Zustand)

```ts
// Key behaviours:
setActiveToken(token)  // clears selectedText
setSelectedText(text)  // does NOT clear activeToken (they coexist — selection builds on active word)
clearActive()          // clears both
```

## Reading progress

- Stored in localStorage under key `"slovo-reading-progress"` as `{[bookId]: pageNumber}`.
- Restored on mount in `reader/[id]/page.tsx` only when no explicit `?page=` URL param.
- Saved on every `setPage()` call.

## Auto-advance "new" words

- When `setPage(p)` is called, `autoAdvanceNewWords(languageId)` runs first.
- Reads current page tokens from TanStack Query cache, filters `status === "new"`, deduplicates by lowercase surface form.
- Calls `batchUpsertWordStatus(items)` fire-and-forget (errors swallowed so navigation is never blocked).

## Admin — data reset

- `admin/data/page.tsx` has a confirmation input requiring exact text `"DELETE ALL DATA"`.
- Calls `DELETE /admin/data/reset`. Shows counts of deleted books and words on success.

## Planned features (see ADRs before implementing)

- **Grammar explanation** — "Explain grammar" button in `DefinitionPanel` selection mode. Sends selected sentence + token table to `POST /grammar/explain`. Renders annotated token table + LLM prose. (ADR-001)
- **Synonym nuance** — "Synonyms" button in `DefinitionPanel` word mode. Sends `activeToken` context to `POST /synonyms/nuance`. Renders register gradient + contrastive examples. (ADR-002)
- Both features need a user settings UI for `proficiency_level` (A1-C2) and `native_language_code`.

<!-- MEMORY:START -->
# web

_Last updated: 2026-04-15 | 0 active memories, 0 total_

_For deeper context, use memory_search, memory_related, or memory_ask tools._
<!-- MEMORY:END -->
