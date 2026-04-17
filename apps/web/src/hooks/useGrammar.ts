"use client"

import { useMutation } from "@tanstack/react-query"
import { explainGrammar, type GrammarExplainResponse } from "@/src/lib/api/grammar"
import type { TokenWithStatus } from "@/src/lib/api/books"

interface UseGrammarOptions {
  languageCode: string
  register?: string | null
}

export function useGrammar({ languageCode, register }: UseGrammarOptions) {
  return useMutation<GrammarExplainResponse, Error, TokenWithStatus[]>({
    mutationFn: (tokens) => {
      const filtered = tokens
        .filter((t) => t.pos !== "PUNCT")
        .map((t) => ({
          w: t.w,
          l: t.l,
          pos: t.pos,
          feats: t.f ?? "",
          dep_head: t.dep_head ?? 0,
          dep_rel: t.dep_rel ?? "",
        }))
      return explainGrammar(filtered, languageCode, register)
    },
  })
}
