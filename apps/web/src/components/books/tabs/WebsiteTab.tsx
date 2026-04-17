"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Globe, Search } from "lucide-react"
import { previewWebsite, importWebsite, type WebsitePreview } from "@/src/lib/api/website"
import { Spinner } from "@/src/components/ui/Spinner"
import { ApiError } from "@/src/lib/api/client"
import { useAuth } from "@/src/stores/auth"
import { websiteUrlSchema } from "@/src/lib/schemas/import"

export function WebsiteTab({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [url, setUrl] = useState("")
  const [preview, setPreview] = useState<WebsitePreview | null>(null)
  const [title, setTitle] = useState("")
  const [urlError, setUrlError] = useState("")
  const [previewError, setPreviewError] = useState("")
  const [error, setError] = useState("")
  const { activeLanguage } = useAuth()

  const previewMutation = useMutation({
    mutationFn: () => previewWebsite(url.trim()),
    onSuccess: (data) => {
      setPreview(data)
      setTitle(data.title)
      setPreviewError("")
    },
    onError: (err) => {
      setPreviewError(err instanceof ApiError ? err.message : "Could not extract content from this URL.")
      setPreview(null)
    },
  })

  const importMutation = useMutation({
    mutationFn: () => {
      if (!activeLanguage) throw new Error("No active language set")
      return importWebsite({
        url: url.trim(),
        title: title.trim() || preview?.title || url,
        language_id: activeLanguage.id,
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
    const result = websiteUrlSchema.safeParse({ url: url.trim() })
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

  return (
    <div className="space-y-4">
      <div>
        <label className="mb-1.5 block text-sm font-medium text-zinc-300">Website URL</label>
        <div className="flex gap-2">
          <input
            type="url"
            value={url}
            onChange={(e) => { setUrl(e.target.value); setPreview(null); setPreviewError(""); setUrlError("") }}
            placeholder="https://example.com/article"
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
          <div className="rounded-lg border border-zinc-800 bg-zinc-800/50 p-3">
            <p className="text-sm font-medium text-zinc-200">{preview.title}</p>
            {preview.author && (
              <p className="mt-0.5 text-xs text-zinc-500">{preview.author}</p>
            )}
            <p className="mt-1.5 text-xs text-zinc-500 line-clamp-3">{preview.excerpt}</p>
            <p className="mt-1.5 text-xs text-zinc-400">
              {preview.word_count.toLocaleString()} words
            </p>
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
          disabled={!preview || importMutation.isPending}
          onClick={() => importMutation.mutate()}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
        >
          {importMutation.isPending && <Spinner className="h-4 w-4" />}
          <Globe className="h-3.5 w-3.5" />
          Import
        </button>
      </div>
    </div>
  )
}
