import type { TokenWithStatus } from "./api/books"

/**
 * Return the lemma for a token, falling back to the surface form when no
 * lemma is available (old pages, out-of-vocabulary tokens). The result is
 * lowercased — our vocabulary table is keyed by lowercase lemma since migration
 * 0042. Frontend code should ALWAYS use this instead of `token.l || token.w`
 * directly, to avoid accidental case-mismatches.
 */
export function getLemmaKey(token: Pick<TokenWithStatus, "l" | "w">): string {
  return (token.l || token.w).toLowerCase()
}
