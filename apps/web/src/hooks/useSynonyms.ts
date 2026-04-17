"use client"

import { useMutation } from "@tanstack/react-query"
import { getSynonymNuance, type SynonymNuanceResponse } from "@/src/lib/api/synonyms"

interface SynonymArgs {
  word: string
  pos: string
  lemma: string
  languageId: number
  languageCode: string
}

export function useSynonyms() {
  return useMutation<SynonymNuanceResponse, Error, SynonymArgs>({
    mutationFn: ({ word, pos, lemma, languageId, languageCode }) =>
      getSynonymNuance({
        language_id: languageId,
        language_code: languageCode,
        word,
        pos,
        lemma,
        context_sentence: undefined,
      }),
  })
}
