"use client"

import { useRef, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, Upload, Trash2, BarChart2 } from "lucide-react"
import {
  uploadFrequencies,
  deleteFrequencies,
  listFrequencyStats,
  type FrequencyImportResult,
  type FrequencyLanguageStat,
} from "@/src/lib/api/admin"
import { getLanguageLabel } from "@/src/lib/language-flags"

function LanguageRow({ stat }: { stat: FrequencyLanguageStat }) {
  const queryClient = useQueryClient()

  const deleteMutation = useMutation({
    mutationFn: () => deleteFrequencies(stat.language_code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["freq-stats"] })
    },
  })

  return (
    <tr className="border-b border-zinc-800">
      <td className="py-3 px-4 text-sm">
        <span className="font-mono text-zinc-300">{stat.language_code}</span>
        <span className="ml-2 text-zinc-500">{getLanguageLabel(stat.language_code)}</span>
      </td>
      <td className="py-3 px-4 text-sm text-zinc-400">
        {stat.entry_count.toLocaleString()} words
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

export default function AdminFrequenciesPage() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [languageCode, setLanguageCode] = useState("pl")
  const [replace, setReplace] = useState(true)
  const [uploadResult, setUploadResult] = useState<FrequencyImportResult | null>(null)
  const [uploadError, setUploadError] = useState("")
  const queryClient = useQueryClient()

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["freq-stats"],
    queryFn: listFrequencyStats,
  })

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
      queryClient.invalidateQueries({ queryKey: ["freq-stats"] })
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
          Upload Word Frequency List
        </h2>
        <p className="mb-4 text-xs text-zinc-500">
          Upload a TSV or CSV frequency list for a language. Expected format (one entry per line):{" "}
          <code className="text-zinc-400">lemma&lt;TAB&gt;rank[&lt;TAB&gt;per_million]</code>.
          Lines starting with <code className="text-zinc-400">#</code> and header rows are skipped.
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

      {/* Loaded languages */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-zinc-300 uppercase tracking-wide">
          Loaded Frequency Lists
        </h2>
        {statsLoading ? (
          <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
        ) : !stats?.length ? (
          <div className="flex flex-col items-center gap-2 py-10 text-zinc-600">
            <BarChart2 className="h-8 w-8" />
            <p className="text-sm">No frequency data loaded yet.</p>
          </div>
        ) : (
          <div className="rounded-xl border border-zinc-800 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900">
                  <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Language</th>
                  <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Words</th>
                  <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-zinc-950">
                {stats.map((s) => (
                  <LanguageRow key={s.language_code} stat={s} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Tier reference */}
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
        <h2 className="mb-3 text-sm font-semibold text-zinc-300 uppercase tracking-wide">
          Frequency tiers
        </h2>
        <div className="grid grid-cols-2 gap-2 text-xs">
          {[
            { tier: "Very common", range: "rank ≤ 1,000", color: "text-green-400" },
            { tier: "Common", range: "rank ≤ 5,000", color: "text-sky-400" },
            { tier: "Uncommon", range: "rank ≤ 20,000", color: "text-yellow-400" },
            { tier: "Rare", range: "rank ≤ 65,000", color: "text-zinc-400" },
            { tier: "Very rare", range: "rank > 65,000", color: "text-zinc-600" },
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
