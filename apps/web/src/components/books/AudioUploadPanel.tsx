"use client"

import { Loader2, Volume2 } from "lucide-react"
import type { BookDetail } from "@/src/lib/api/books"

interface AudioUploadPanelProps {
  book: BookDetail
}

export function AudioUploadPanel({ book }: AudioUploadPanelProps) {
  if (book.status !== "completed" || !book.has_audio_overlay) return null

  return (
    <div className="rounded-lg border border-zinc-700 bg-zinc-800/50 p-4">
      <div className="flex items-center gap-2 text-sm text-zinc-300">
        <Volume2 className="h-4 w-4 text-blue-400" />
        <span className="font-medium">Embedded Audio</span>
      </div>
      {book.audio_overlay_status === "complete" ? (
        <p className="mt-1 text-xs text-green-400">Audio overlay ready</p>
      ) : (
        <div className="mt-1 flex items-center gap-2 text-xs text-zinc-400">
          <Loader2 className="h-3 w-3 animate-spin" />
          Syncing audio overlay…
        </div>
      )}
    </div>
  )
}
