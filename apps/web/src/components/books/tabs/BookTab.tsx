"use client"

import { useState, useRef } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Upload } from "lucide-react"
import { uploadBook } from "@/src/lib/api/books"
import { Spinner } from "@/src/components/ui/Spinner"
import { ApiError } from "@/src/lib/api/client"
import { cn } from "@/src/lib/cn"
import { useAuth } from "@/src/stores/auth"

export function BookTab({ onClose }: { onClose: () => void }) {
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
