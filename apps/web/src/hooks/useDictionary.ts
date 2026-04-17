"use client"

import { useQuery } from "@tanstack/react-query"
import { lookup } from "@/src/lib/api/dictionary"

interface UseDictionaryOptions {
  word: string
  language: string
  enabled?: boolean
}

export function useDictionary({ word, language, enabled = true }: UseDictionaryOptions) {
  return useQuery({
    queryKey: ["dictionary", word, language],
    queryFn: () => lookup(word, language.slice(0, 2).toLowerCase(), "en"),
    enabled: enabled && !!word && !!language,
    staleTime: Infinity,
  })
}
