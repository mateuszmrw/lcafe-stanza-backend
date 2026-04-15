"use client"

import { useState, useRef } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Upload, Video, Globe, Search } from "lucide-react"
import { uploadBook } from "@/src/lib/api/books"
import { previewYouTube, importYouTube, type YouTubePreview } from "@/src/lib/api/youtube"
import { previewWebsite, importWebsite, type WebsitePreview } from "@/src/lib/api/website"
import { Dialog } from "@/src/components/ui/Dialog"
import { Spinner } from "@/src/components/ui/Spinner"
import { ApiError } from "@/src/lib/api/client"
import { cn } from "@/src/lib/cn"
import { useAuth } from "@/src/stores/auth"

interface ImportBookDialogProps {
  open: boolean
  onClose: () => void
}

type Tab = "book" | "youtube" | "website"

export function ImportBookDialog({ open, onClose }: ImportBookDialogProps) {
  const [tab, setTab] = useState<Tab>("book")

  function handleClose() {
    onClose()
    // Reset tab after dialog close animation
    setTimeout(() => setTab("book"), 200)
  }

  return (
    <Dialog open={open} onClose={handleClose} title="Import Content">
      {/* Tabs */}
      <div className="mb-5 flex rounded-lg border border-zinc-800 bg-zinc-800/50 p-0.5">
        <TabButton active={tab === "book"} onClick={() => setTab("book")}>
          <Upload className="h-3.5 w-3.5" />
          Book / EPUB
        </TabButton>
        <TabButton active={tab === "youtube"} onClick={() => setTab("youtube")}>
          <Video className="h-3.5 w-3.5" />
          YouTube
        </TabButton>
        <TabButton active={tab === "website"} onClick={() => setTab("website")}>
          <Globe className="h-3.5 w-3.5" />
          Website
        </TabButton>
      </div>

      {tab === "book" ? (
        <BookTab onClose={handleClose} />
      ) : tab === "youtube" ? (
        <YouTubeTab onClose={handleClose} />
      ) : (
        <WebsiteTab onClose={handleClose} />
      )}
    </Dialog>
  )
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-1 items-center justify-center gap-1.5 rounded-md py-1.5 text-sm font-medium transition",
        active
          ? "bg-zinc-700 text-zinc-100 shadow-sm"
          : "text-zinc-400 hover:text-zinc-200"
      )}
    >
      {children}
    </button>
  )
}

// ─── Book Tab ────────────────────────────────────────────────────────────────

function BookTab({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState("")
  const [register, setRegister] = useState("")
  const [error, setError] = useState("")
  const { activeLanguage } = useAuth()

  const mutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("No file selected")
      if (!activeLanguage) throw new Error("No active language set")
      return uploadBook(file, activeLanguage.id, title.trim() || file.name.replace(/\.epub$/i, ""), register || null)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["books"] })
      onClose()
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Upload failed. Please try again.")
    },
  })

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
        <input
          ref={fileRef}
          type="file"
          accept=".epub,.pdf"
          className="hidden"
          onChange={(e) => { setFile(e.target.files?.[0] ?? null); setError("") }}
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className={cn(
            "flex w-full flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed py-8 transition",
            file
              ? "border-blue-500 bg-blue-900/10 text-blue-300"
              : "border-zinc-700 text-zinc-500 hover:border-zinc-500 hover:text-zinc-300"
          )}
        >
          <Upload className="h-6 w-6" />
          <span className="text-sm">
            {file ? file.name : "Click to choose an EPUB or PDF file"}
          </span>
        </button>
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-zinc-300">Title</label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={file ? file.name.replace(/\.(epub|pdf)$/i, "") : "Book title"}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-zinc-300">Language</label>
        <p className="rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-2 text-sm text-zinc-400">
          {activeLanguage.name}
        </p>
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-zinc-300">
          Register <span className="font-normal text-zinc-500">(optional)</span>
        </label>
        <select
          value={register}
          onChange={(e) => setRegister(e.target.value)}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Unspecified</option>
          <option value="formal">Formal</option>
          <option value="literary">Literary</option>
          <option value="informal">Informal</option>
          <option value="technical">Technical</option>
        </select>
      </div>

      {error && (
        <p className="rounded-lg bg-red-900/30 px-3 py-2 text-sm text-red-400">{error}</p>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <button type="button" onClick={onClose} className="rounded-lg px-4 py-2 text-sm text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-100">
          Cancel
        </button>
        <button
          type="button"
          disabled={!file || mutation.isPending}
          onClick={() => mutation.mutate()}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
        >
          {mutation.isPending && <Spinner className="h-4 w-4" />}
          Import
        </button>
      </div>
    </div>
  )
}

// ─── YouTube Tab ─────────────────────────────────────────────────────────────

function YouTubeTab({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [url, setUrl] = useState("")
  const [preview, setPreview] = useState<YouTubePreview | null>(null)
  const [title, setTitle] = useState("")
  const [subtitleLang, setSubtitleLang] = useState("")
  const [useAuto, setUseAuto] = useState(true)
  const [previewError, setPreviewError] = useState("")
  const [error, setError] = useState("")
  const { activeLanguage } = useAuth()

  const previewMutation = useMutation({
    mutationFn: () => previewYouTube(url.trim()),
    onSuccess: (data) => {
      setPreview(data)
      setTitle(data.title)
      // Default to first non-auto subtitle, or first auto if none
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
      {/* URL input + preview button */}
      <div>
        <label className="mb-1.5 block text-sm font-medium text-zinc-300">YouTube URL</label>
        <div className="flex gap-2">
          <input
            type="url"
            value={url}
            onChange={(e) => { setUrl(e.target.value); setPreview(null); setPreviewError("") }}
            placeholder="https://youtube.com/watch?v=..."
            className="min-w-0 flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="button"
            disabled={!url.trim() || previewMutation.isPending}
            onClick={() => previewMutation.mutate()}
            className="flex shrink-0 items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-300 transition hover:bg-zinc-700 disabled:opacity-50"
          >
            {previewMutation.isPending ? <Spinner className="h-3.5 w-3.5" /> : <Search className="h-3.5 w-3.5" />}
            Preview
          </button>
        </div>
        {previewError && (
          <p className="mt-1.5 text-xs text-red-400">{previewError}</p>
        )}
      </div>

      {/* Preview card */}
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

          {/* Title override */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-300">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Language */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-300">Language</label>
            <p className="rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-2 text-sm text-zinc-400">
              {activeLanguage.name}
            </p>
          </div>

          {/* Subtitle track */}
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

// ─── Website Tab ────────────────────────────────────────────────────────────

function WebsiteTab({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [url, setUrl] = useState("")
  const [preview, setPreview] = useState<WebsitePreview | null>(null)
  const [title, setTitle] = useState("")
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

  if (!activeLanguage) {
    return (
      <p className="rounded-lg bg-amber-900/30 px-3 py-2 text-sm text-amber-400">
        Select an active language from the sidebar before importing.
      </p>
    )
  }

  return (
    <div className="space-y-4">
      {/* URL input + preview button */}
      <div>
        <label className="mb-1.5 block text-sm font-medium text-zinc-300">Website URL</label>
        <div className="flex gap-2">
          <input
            type="url"
            value={url}
            onChange={(e) => { setUrl(e.target.value); setPreview(null); setPreviewError("") }}
            placeholder="https://example.com/article"
            className="min-w-0 flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="button"
            disabled={!url.trim() || previewMutation.isPending}
            onClick={() => previewMutation.mutate()}
            className="flex shrink-0 items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-300 transition hover:bg-zinc-700 disabled:opacity-50"
          >
            {previewMutation.isPending ? <Spinner className="h-3.5 w-3.5" /> : <Search className="h-3.5 w-3.5" />}
            Preview
          </button>
        </div>
        {previewError && (
          <p className="mt-1.5 text-xs text-red-400">{previewError}</p>
        )}
      </div>

      {/* Preview card */}
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

          {/* Title override */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-300">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Language */}
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

function formatDuration(ms: number): string {
  const totalSec = Math.floor(ms / 1000)
  const h = Math.floor(totalSec / 3600)
  const m = Math.floor((totalSec % 3600) / 60)
  const s = totalSec % 60
  if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
  return `${m}:${s.toString().padStart(2, "0")}`
}
