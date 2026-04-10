"use client"

import { useEffect } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { env } from "@/src/env"
import { getAuthStore } from "@/src/stores/auth"

export function useBookStatus(bookId: string, enabled: boolean) {
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!enabled) return

    const { accessToken } = getAuthStore()
    const url = `${env.apiUrl}/books/${bookId}/status/stream${accessToken ? `?token=${accessToken}` : ""}`
    const source = new EventSource(url)

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as { type: string }
        if (data.type === "completed" || data.type === "failed") {
          queryClient.invalidateQueries({ queryKey: ["books"] })
          source.close()
        }
      } catch {
        // ignore malformed events
      }
    }

    source.onerror = () => {
      source.close()
    }

    return () => source.close()
  }, [bookId, enabled, queryClient])
}
