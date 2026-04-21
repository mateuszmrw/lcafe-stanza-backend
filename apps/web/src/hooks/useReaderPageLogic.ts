"use client"

import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { getBookPages, getPagePhrases, type ConstituencyPhrase, type TokenWithStatus } from "@/src/lib/api/books"
import { listPhrases } from "@/src/lib/api/phrases"

interface Args {
  bookId: string
  page: number
  languageId: number
  noWordSpacing: boolean
}

function buildPhraseTokenSet(
  tokens: TokenWithStatus[],
  phrases: { text: string; book_id?: string | null; page?: number | null }[],
  noSpace: boolean,
): Set<number> {
  const result = new Set<number>()
  const sep = noSpace ? "" : " "
  for (const phrase of phrases) {
    const target = phrase.text.trim()
    for (let start = 0; start < tokens.length; start++) {
      let text = ""
      for (let end = start; end < tokens.length; end++) {
        text = end === start ? tokens[end].w : text + sep + tokens[end].w
        if (text.trim() === target) {
          for (let i = start; i <= end; i++) result.add(i)
          break
        }
        if (text.length > target.length + 2) break
      }
    }
  }
  return result
}

export function useReaderPageLogic({ bookId, page, languageId, noWordSpacing }: Args) {
  const { data, isLoading } = useQuery({
    queryKey: ["book-pages", bookId, page],
    queryFn: () => getBookPages(bookId, page, 1),
    placeholderData: (prev) => prev,
    refetchInterval: (query) =>
      query.state.data?.items[0]?.status === "pending" ? 3000 : false,
  })

  const { data: phrasesData } = useQuery({
    queryKey: ["phrases", languageId],
    queryFn: () => listPhrases(languageId, undefined, 1, 500),
    staleTime: 30_000,
  })

  const currentPage = data?.items[0]

  const { data: constituentPhrases = [] } = useQuery<ConstituencyPhrase[]>({
    queryKey: ["page-phrases", bookId, currentPage?.id],
    queryFn: () => getPagePhrases(bookId, currentPage!.id),
    enabled: !!currentPage?.id && currentPage.status === "ready",
    staleTime: Infinity,
  })

  const phraseTokenIndices = useMemo(() => {
    if (!currentPage || !phrasesData) return new Set<number>()
    const pagePhrase = phrasesData.items.filter(
      (p) => p.book_id === bookId && p.page === page,
    )
    return buildPhraseTokenSet(currentPage.tokens, pagePhrase, noWordSpacing)
  }, [currentPage, phrasesData, bookId, page, noWordSpacing])

  return { currentPage, isLoading, phraseTokenIndices, constituentPhrases }
}
