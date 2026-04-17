"use client"

import { useQuery } from "@tanstack/react-query"
import { translate, getTranslationAvailable } from "@/src/lib/api/translation"

export function useTranslationAvailability() {
  const { data } = useQuery({
    queryKey: ["translation-available"],
    queryFn: getTranslationAvailable,
    staleTime: Infinity,
  })
  return data?.available ?? false
}

interface UseTranslationOptions {
  text: string | null
  language: string
  enabled?: boolean
}

export function useTranslation({ text, language, enabled = true }: UseTranslationOptions) {
  return useQuery({
    queryKey: ["translation", text, language],
    queryFn: () => translate(text!, language),
    enabled: enabled && !!text && !!language,
    staleTime: Infinity,
    retry: false,
  })
}
