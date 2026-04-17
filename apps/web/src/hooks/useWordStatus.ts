"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { upsertWordStatus } from "@/src/lib/api/vocabulary"
import { getLemmaKey } from "@/src/lib/tokens"
import type { TokenWithStatus } from "@/src/lib/api/books"
import type { PageListResponse } from "@/src/lib/api/books"

interface UseWordStatusOptions {
  languageId: number
  token: (TokenWithStatus & { wordId?: string }) | null
  sentenceContext?: string | null
  onSuccess?: (status: string) => void
}

export function useWordStatus({ languageId, token, sentenceContext, onSuccess }: UseWordStatusOptions) {
  const queryClient = useQueryClient()
  const lemmaKey = token ? getLemmaKey(token) : ""

  const mutation = useMutation({
    mutationFn: ({ status, hint }: { status: string; hint?: string | null }) =>
      upsertWordStatus({
        word: lemmaKey,
        status,
        language_id: languageId,
        lemma: token?.l || "",
        pos: token?.pos || "",
        reading: token?.r || "",
        gender: token?.g || "",
        feats: token?.f || "",
        hint,
        sentence_context: sentenceContext ?? undefined,
      }),
    onSuccess: (_, { status }) => {
      queryClient.invalidateQueries({ queryKey: ["vocabulary"] })
      queryClient.invalidateQueries({ queryKey: ["books"] })
      queryClient.setQueriesData<PageListResponse>(
        { queryKey: ["book-pages"] },
        (old) => {
          if (!old) return old
          return {
            ...old,
            items: old.items.map((p) => ({
              ...p,
              tokens: p.tokens.map((t) =>
                getLemmaKey(t) === lemmaKey
                  ? { ...t, status: status as TokenWithStatus["status"] }
                  : t
              ),
            })),
          }
        }
      )
      onSuccess?.(status)
    },
  })

  return { mutate: mutation.mutate, isPending: mutation.isPending, lemmaKey }
}
