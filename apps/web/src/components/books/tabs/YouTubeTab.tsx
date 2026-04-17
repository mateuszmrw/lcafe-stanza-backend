"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Video, Search } from "lucide-react"
import { previewYouTube, importYouTube, type YouTubePreview } from "@/src/lib/api/youtube"
import { Spinner } from "@/src/components/ui/Spinner"
import { ApiError } from "@/src/lib/api/client"
import { useAuth } from "@/src/stores/auth"
import { youtubeUrlSchema } from "@/src/lib/schemas/import"

function formatDuration(ms: number): string {
  const totalSec = Math.floor(ms / 1000)
  const h = Math.floor(totalSec / 3600)
  const m = Math.floor((totalSec % 3600) / 60)
  const s = totalSec % 60
  if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
  return `${m}:${s.toString().padStart(2, "0")}`
}

export function YouTubeTab({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [url, setUrl] = useState("")
  const [preview, setPreview] = useState<YouTubePreview | null>(null)
  const [title, setTitle] = useState("")
  const [subtitleLang, setSubtitleLang] = useState("")
  const [useAuto, setUseAuto] = useState(true)
  const [urlError, setUrlError] = useState("")
  const [previewError, setPreviewError] = useState("")
  const [error, setError] = useState("")
  const { activeLanguage } = useAuth()

  const previewMutation = useMutation({
    mutationFn: () => previewYouTube(url.trim()),
    onSuccess: (data) => {
      setPreview(data)
      setTitle(data.title)
      const first = data.available_subtitles.find((s) => !s.is_auto)
        ?? data.available_subtitles[0]
      setSubtitleLang(first?.lang_code ?? "")
      setPreviewError("")
    },
    onError: (err) => {
      setPreviewError(err instanceof ApiError ? err.message : "Could not fetch video info.")
      setPreview(null)
    },
  })

  const importMutation = useMutation({
    mutationFn: () => {
      if (!activeLanguage) throw new Error("No active language set")
      return importYouTube({
        url: url.trim(),
        title: (title.trim() || preview?.title) ?? url,
        language_id: activeLanguage.id,
        subtitle_lang_code: subtitleLang,
        use_auto_captions: useAuto,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["books"] })
      onClose()
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Import failed. Please try again.")
    },
  })

  function handlePreview() {
    const result = youtubeUrlSchema.safeParse({ url: url.trim() })
    if (!result.success) {
      setUrlError(result.error.issues[0]?.message ?? "Invalid URL")
      return
    }
    setUrlError("")
    previewMutation.mutate()
  }

  if (!activeLanguage) {
    return (
      <p className="rounded-lg bg-amber-900/30 px-3 py-2 text-sm text-amber-400">
        Select an active language from the sidebar before importing.
      </p>
    )
  }

  const selectedSubtitle = preview?.available_subtitles.find((s) => s.lang_code === subtitleLang)

  return (
    <div className="space-y-4">
      <div>
        <label className="mb-1.5 block text-sm font-medium text-zinc-300">YouTube URL</label>
        <div className="flex gap-2">
          <input
            type="url"
            value={url}
            onChange={(e) => { setUrl(e.target.value); setPreview(null); setPreviewError(""); setUrlError("") }}
            placeholder="https://youtube.com/watch?v=..."
            className="min-w-0 flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="button"
            disabled={!url.trim() || previewMutation.isPending}
            onClick={handlePreview}
            className="flex shrink-0 items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-300 transition hover:bg-zinc-700 disabled:opacity-50"
          >
            {previewMutation.isPending ? <Spinner className="h-3.5 w-3.5" /> : <Search className="h-3.5 w-3.5" />}
            Preview
          </button>
        </div>
        {urlError && <p className="mt-1.5 text-xs text-red-400">{urlError}</p>}
        {previewError && <p className="mt-1.5 text-xs text-red-400">{previewError}</p>}
      </div>

      {preview && (
        <>
          <div className="flex gap-3 rounded-lg border border-zinc-800 bg-zinc-800/50 p-3">
            {preview.thumbnail_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={preview.thumbnail_url}
                alt=""
                className="h-16 w-28 shrink-0 rounded-md object-cover"
              />
            )}
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-zinc-200">{preview.title}</p>
              {preview.channel_name && (
                <p className="mt-0.5 truncate text-xs text-zinc-500">{preview.channel_name}</p>
              )}
              {preview.duration_ms && (
                <p className="mt-1 text-xs text-zinc-500">{formatDuration(preview.duration_ms)}</p>
              )}
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-300">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-300">Language</label>
            <p className="rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-2 text-sm text-zinc-400">
              {activeLanguage.name}
            </p>
          </div>

          {preview.available_subtitles.length > 0 ? (
            <div>
              <label className="mb-1.5 block text-sm font-medium text-zinc-300">Subtitles</label>
              <select
                value={subtitleLang}
                onChange={(e) => setSubtitleLang(e.target.value)}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
              >
                {preview.available_subtitles.map((s) => (
                  <option key={`${s.lang_code}-${s.is_auto}`} value={s.lang_code}>
                    {s.label}{s.is_auto ? " (auto-generated)" : ""}
                  </option>
                ))}
              </select>
              {selectedSubtitle?.is_auto && (
                <p className="mt-1 text-xs text-zinc-500">
                  Auto-generated captions may have errors.
                </p>
              )}
            </div>
          ) : (
            <div>
              <label className="mb-1.5 block text-sm font-medium text-zinc-300">Subtitles</label>
              <p className="rounded-lg bg-amber-900/30 px-3 py-2 text-sm text-amber-400">
                No subtitles found. You can upload an .srt file after import.
              </p>
              <label className="mt-2 flex items-center gap-2 text-sm text-zinc-400">
                <input
                  type="checkbox"
                  checked={useAuto}
                  onChange={(e) => setUseAuto(e.target.checked)}
                  className="rounded border-zinc-600 bg-zinc-800 accent-blue-500"
                />
                Try auto-generated captions
              </label>
            </div>
          )}
        </>
      )}

      {error && (
        <p className="rounded-lg bg-red-900/30 px-3 py-2 text-sm text-red-400">{error}</p>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <button type="button" onClick={onClose} className="rounded-lg px-4 py-2 text-sm text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-100">
          Cancel
        </button>
        <button
          type="button"
          disabled={!preview || !subtitleLang || importMutation.isPending}
          onClick={() => importMutation.mutate()}
          className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-500 disabled:opacity-50"
        >
          {importMutation.isPending && <Spinner className="h-4 w-4" />}
          <Video className="h-3.5 w-3.5" />
          Import
        </button>
      </div>
    </div>
  )
}
