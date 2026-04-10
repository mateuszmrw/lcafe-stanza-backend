"use client"

import { useRef, useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { Loader2, Upload, Trash2 } from "lucide-react"
import {
  uploadFrequencies,
  deleteFrequencies,
  type FrequencyImportResult,
} from "@/src/lib/api/admin"

export default function AdminFrequenciesPage() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [languageCode, setLanguageCode] = useState("pl")
  const [replace, setReplace] = useState(true)
  const [uploadResult, setUploadResult] = useState<FrequencyImportResult | null>(null)
  const [uploadError, setUploadError] = useState("")

  const uploadMutation = useMutation({
    mutationFn: async () => {
      const file = fileRef.current?.files?.[0]
      if (!file) throw new Error("No file selected")
      return uploadFrequencies(languageCode, file, replace)
    },
    onSuccess: (result) => {
      setUploadResult(result)
      setUploadError("")
      if (fileRef.current) fileRef.current.value = ""
    },
    onError: (e: unknown) => {
      setUploadError(e instanceof Error ? e.message : "Upload failed")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteFrequencies(languageCode),
    onSuccess: (result) => {
      setUploadResult(result)
      setUploadError("")
    },
    onError: (e: unknown) => {
      setUploadError(e instanceof Error ? e.message : "Delete failed")
    },
  })

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <h2 className="mb-1 text-sm font-semibold text-zinc-300 uppercase tracking-wide">
          Upload Word Frequency List
        </h2>
        <p className="mb-4 text-xs text-zinc-500">
          Upload a TSV or CSV frequency list for a language. Expected format (one entry per line):{" "}
          <code className="text-zinc-400">lemma&lt;TAB&gt;rank[&lt;TAB&gt;per_million]</code>.
          Lines starting with <code className="text-zinc-400">#</code> are skipped.
          A header row (<code className="text-zinc-400">lemma</code> in first column) is auto-detected and skipped.
          Compatible with OpenSubtitles2018 and OPUS frequency lists.
        </p>

        <div className="space-y-4">
          <div className="flex items-end gap-3">
            <div>
              <label className="block text-xs text-zinc-500 mb-1.5">Language code</label>
              <input
                value={languageCode}
                onChange={(e) => setLanguageCode(e.target.value.toLowerCase())}
                placeholder="pl"
                className="w-20 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500 font-mono"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs text-zinc-500 mb-1.5">TSV / CSV file</label>
              <input
                ref={fileRef}
                type="file"
                accept=".tsv,.txt,.csv"
                className="block w-full text-sm text-zinc-400 file:mr-3 file:rounded-md file:border-0 file:bg-zinc-700 file:px-3 file:py-1.5 file:text-sm file:text-zinc-200 hover:file:bg-zinc-600"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="replace-freq"
              checked={replace}
              onChange={(e) => setReplace(e.target.checked)}
              className="rounded border-zinc-600 bg-zinc-800"
            />
            <label htmlFor="replace-freq" className="text-sm text-zinc-400">
              Replace existing entries for this language
            </label>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => uploadMutation.mutate()}
              disabled={uploadMutation.isPending || deleteMutation.isPending}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
            >
              {uploadMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              {uploadMutation.isPending ? "Uploading…" : "Upload"}
            </button>

            <button
              onClick={() => deleteMutation.mutate()}
              disabled={uploadMutation.isPending || deleteMutation.isPending || !languageCode}
              className="flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-red-400 hover:bg-zinc-800 disabled:opacity-50"
            >
              {deleteMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
              Delete all for language
            </button>
          </div>

          {uploadResult && (
            <p className="text-sm text-green-400">
              Done —{" "}
              {uploadResult.inserted > 0
                ? `${uploadResult.inserted.toLocaleString()} entries inserted`
                : "no entries inserted"}
              {uploadResult.deleted > 0 && `, ${uploadResult.deleted.toLocaleString()} deleted`}.
            </p>
          )}
          {uploadError && <p className="text-sm text-red-400">{uploadError}</p>}
        </div>
      </section>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
        <h2 className="mb-2 text-sm font-semibold text-zinc-300 uppercase tracking-wide">
          About frequency tiers
        </h2>
        <div className="grid grid-cols-2 gap-2 text-xs">
          {[
            { tier: "Very common", range: "rank ≤ 1,000", color: "text-green-400" },
            { tier: "Common", range: "rank ≤ 5,000", color: "text-sky-400" },
            { tier: "Uncommon", range: "rank ≤ 20,000", color: "text-yellow-400" },
            { tier: "Rare", range: "rank > 20,000", color: "text-zinc-500" },
          ].map(({ tier, range, color }) => (
            <div key={tier} className="flex items-center gap-2">
              <span className={`font-medium ${color}`}>{tier}</span>
              <span className="text-zinc-600">{range}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
