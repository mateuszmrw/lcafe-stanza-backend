"use client"

import { useRef, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, Upload, Trash2, BookOpen, ArrowRight } from "lucide-react"
import {
  getDictionaryStats,
  uploadDictionary,
  deleteDictionaryPair,
  type DictionaryStats,
} from "@/src/lib/api/admin"

function PairRow({ stat }: { stat: DictionaryStats }) {
  const queryClient = useQueryClient()

  const deleteMutation = useMutation({
    mutationFn: () => deleteDictionaryPair(stat.source_lang, stat.target_lang),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dict-stats"] })
    },
  })

  return (
    <tr className="border-b border-zinc-800">
      <td className="py-3 px-4">
        <span className="inline-flex items-center gap-1.5 text-sm">
          <code className="font-mono text-zinc-300">{stat.source_lang}</code>
          <ArrowRight className="h-3 w-3 text-zinc-600" />
          <code className="font-mono text-zinc-300">{stat.target_lang}</code>
        </span>
      </td>
      <td className="py-3 px-4 text-sm text-zinc-400">
        {stat.entry_count.toLocaleString()} entries
      </td>
      <td className="py-3 px-4">
        <button
          onClick={() => deleteMutation.mutate()}
          disabled={deleteMutation.isPending}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-red-400 hover:bg-zinc-800 transition disabled:opacity-50"
        >
          {deleteMutation.isPending ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Trash2 className="h-3 w-3" />
          )}
          Delete
        </button>
      </td>
    </tr>
  )
}

export default function AdminDictionaryPage() {
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [sourceLang, setSourceLang] = useState("ru")
  const [targetLang, setTargetLang] = useState("en")
  const [replace, setReplace] = useState(true)
  const [uploadResult, setUploadResult] = useState<{ inserted: number; deleted: number } | null>(null)
  const [uploadError, setUploadError] = useState("")

  const { data: stats, isLoading } = useQuery({
    queryKey: ["dict-stats"],
    queryFn: getDictionaryStats,
  })

  const uploadMutation = useMutation({
    mutationFn: async () => {
      const file = fileRef.current?.files?.[0]
      if (!file) throw new Error("No file selected")
      return uploadDictionary(sourceLang, targetLang, file, replace)
    },
    onSuccess: (result) => {
      setUploadResult(result)
      setUploadError("")
      queryClient.invalidateQueries({ queryKey: ["dict-stats"] })
      if (fileRef.current) fileRef.current.value = ""
    },
    onError: (e: unknown) => {
      setUploadError(e instanceof Error ? e.message : "Upload failed")
    },
  })

  return (
    <div className="space-y-8">
      {/* Upload section */}
      <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <h2 className="mb-1 text-sm font-semibold text-zinc-300 uppercase tracking-wide">
          Upload Dictionary
        </h2>
        <p className="mb-4 text-xs text-zinc-500">
          Upload a bilingual JSONL dictionary. Each entry should have{" "}
          <code className="text-zinc-400">word</code>,{" "}
          <code className="text-zinc-400">pos</code>, and{" "}
          <code className="text-zinc-400">senses[].glosses[]</code> fields.
          Source is the language being read; target is the language definitions are written in.
          Compatible with{" "}
          <span className="text-zinc-400">kaikki.org</span> exports.
        </p>

        <div className="space-y-4">
          <div className="flex items-end gap-3">
            <div>
              <label className="block text-xs text-zinc-500 mb-1.5">Source language</label>
              <input
                value={sourceLang}
                onChange={(e) => setSourceLang(e.target.value.toLowerCase())}
                placeholder="ru"
                className="w-20 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500 font-mono"
              />
            </div>
            <ArrowRight className="h-4 w-4 text-zinc-600 mb-2.5" />
            <div>
              <label className="block text-xs text-zinc-500 mb-1.5">Target language</label>
              <input
                value={targetLang}
                onChange={(e) => setTargetLang(e.target.value.toLowerCase())}
                placeholder="en"
                className="w-20 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500 font-mono"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs text-zinc-500 mb-1.5">JSONL file</label>
              <input
                ref={fileRef}
                type="file"
                accept=".jsonl,.json"
                className="block w-full text-sm text-zinc-400 file:mr-3 file:rounded-md file:border-0 file:bg-zinc-700 file:px-3 file:py-1.5 file:text-sm file:text-zinc-200 hover:file:bg-zinc-600"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="replace"
              checked={replace}
              onChange={(e) => setReplace(e.target.checked)}
              className="rounded border-zinc-600 bg-zinc-800"
            />
            <label htmlFor="replace" className="text-sm text-zinc-400">
              Replace existing entries for this language pair
            </label>
          </div>

          <button
            onClick={() => uploadMutation.mutate()}
            disabled={uploadMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
          >
            {uploadMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            {uploadMutation.isPending ? "Uploading…" : "Upload"}
          </button>

          {uploadResult && (
            <p className="text-sm text-green-400">
              Done — {uploadResult.inserted.toLocaleString()} entries inserted
              {uploadResult.deleted > 0 && `, ${uploadResult.deleted.toLocaleString()} deleted`}.
            </p>
          )}
          {uploadError && <p className="text-sm text-red-400">{uploadError}</p>}
        </div>
      </section>

      {/* Loaded pairs */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-zinc-300 uppercase tracking-wide">
          Loaded Language Pairs
        </h2>
        {isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
        ) : !stats?.length ? (
          <div className="flex flex-col items-center gap-2 py-10 text-zinc-600">
            <BookOpen className="h-8 w-8" />
            <p className="text-sm">No dictionary data loaded yet.</p>
          </div>
        ) : (
          <div className="rounded-xl border border-zinc-800 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900">
                  <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Pair</th>
                  <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Entries</th>
                  <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-zinc-950">
                {stats.map((s) => (
                  <PairRow key={`${s.source_lang}-${s.target_lang}`} stat={s} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
