"use client"

import { useRef, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowRight, BookOpen, ChevronDown, ChevronUp, Loader2, Trash2, Upload } from "lucide-react"
import {
  deleteDictionaryPair,
  deleteDictionarySource,
  getDictionarySources,
  getDictionaryStats,
  updateDictionarySource,
  uploadDictionary,
  type DictionarySourceResponse,
  type DictionaryStats,
} from "@/src/lib/api/admin"

// ── Supported source slugs (mirrors parser_factory.py registry) ───────────────
const SOURCE_SLUGS = [
  { slug: "wiktionary", label: "Wiktionary (kaikki.org JSONL)" },
  { slug: "openrussian", label: "OpenRussian (ZIP from app.togetherdb.com: words + translations + words_forms + verbs + nouns)" },
  { slug: "cc-cedict", label: "CC-CEDICT (ZIP from mdbg.net — cedict_1_0_ts_utf-8_mdbg.zip)" },
  { slug: "dict.cc", label: "dict.cc (TSV bulk download — requires free registration at dict.cc)" },
  { slug: "krdict", label: "KRDICT (ZIP from krdict.korean.go.kr — 한국어기초사전 LMF XML)" },
]

// ── Language pair row ─────────────────────────────────────────────────────────

function PairRow({ stat }: { stat: DictionaryStats }) {
  const queryClient = useQueryClient()
  const deleteMutation = useMutation({
    mutationFn: () => deleteDictionaryPair(stat.source_lang, stat.target_lang),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dict-stats"] }),
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
          {deleteMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
          Delete
        </button>
      </td>
    </tr>
  )
}

// ── Dictionary source row ─────────────────────────────────────────────────────

function SourceRow({ source }: { source: DictionarySourceResponse }) {
  const queryClient = useQueryClient()

  const toggleMutation = useMutation({
    mutationFn: () => updateDictionarySource(source.slug, { is_active: !source.is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dict-sources"] }),
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteDictionarySource(source.slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dict-sources"] })
      queryClient.invalidateQueries({ queryKey: ["dict-stats"] })
    },
  })

  return (
    <tr className="border-b border-zinc-800">
      <td className="py-3 px-4">
        <div>
          <span className="text-sm font-medium text-zinc-200">{source.name}</span>
          <code className="ml-2 text-xs text-zinc-500 font-mono">{source.slug}</code>
        </div>
        {source.description && (
          <p className="mt-0.5 text-xs text-zinc-600">{source.description}</p>
        )}
      </td>
      <td className="py-3 px-4 text-sm text-zinc-400 tabular-nums">
        {source.entry_count.toLocaleString()}
      </td>
      <td className="py-3 px-4 text-sm tabular-nums text-zinc-400">{source.priority}</td>
      <td className="py-3 px-4">
        <button
          onClick={() => toggleMutation.mutate()}
          disabled={toggleMutation.isPending}
          className={`rounded-full px-2 py-0.5 text-xs font-medium transition ${
            source.is_active
              ? "bg-green-900/40 text-green-400 hover:bg-green-900/60"
              : "bg-zinc-800 text-zinc-500 hover:bg-zinc-700"
          }`}
        >
          {source.is_active ? "active" : "inactive"}
        </button>
      </td>
      <td className="py-3 px-4">
        <button
          onClick={() => {
            if (!confirm(`Delete all entries for "${source.name}"? This cannot be undone.`)) return
            deleteMutation.mutate()
          }}
          disabled={deleteMutation.isPending || source.slug === "wiktionary"}
          title={source.slug === "wiktionary" ? "Use the language pair delete below" : undefined}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-red-400 hover:bg-zinc-800 transition disabled:opacity-30"
        >
          {deleteMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
          Delete
        </button>
      </td>
    </tr>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminDictionaryPage() {
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [sourceLang, setSourceLang] = useState("ru")
  const [targetLang, setTargetLang] = useState("en")
  const [sourceSlug, setSourceSlug] = useState("wiktionary")
  const [replace, setReplace] = useState(true)
  const [uploadResult, setUploadResult] = useState<{ inserted: number; deleted: number } | null>(null)
  const [uploadError, setUploadError] = useState("")
  const [showPairs, setShowPairs] = useState(false)

  const { data: sources, isLoading: sourcesLoading } = useQuery({
    queryKey: ["dict-sources"],
    queryFn: getDictionarySources,
  })

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["dict-stats"],
    queryFn: getDictionaryStats,
  })

  const uploadMutation = useMutation({
    mutationFn: async () => {
      const file = fileRef.current?.files?.[0]
      if (!file) throw new Error("No file selected")
      return uploadDictionary(sourceLang, targetLang, file, replace, sourceSlug)
    },
    onSuccess: (result) => {
      setUploadResult(result)
      setUploadError("")
      queryClient.invalidateQueries({ queryKey: ["dict-stats"] })
      queryClient.invalidateQueries({ queryKey: ["dict-sources"] })
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
          Select the dictionary source, language pair, and file to import.
        </p>

        <div className="space-y-4">
          {/* Source selector */}
          <div>
            <label className="block text-xs text-zinc-500 mb-1.5">Dictionary source</label>
            <select
              value={sourceSlug}
              onChange={(e) => setSourceSlug(e.target.value)}
              className="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
            >
              {SOURCE_SLUGS.map(({ slug, label }) => (
                <option key={slug} value={slug}>{label}</option>
              ))}
            </select>
          </div>

          {/* Language pair + file */}
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
              <label className="block text-xs text-zinc-500 mb-1.5">File</label>
              <input
                ref={fileRef}
                type="file"
                accept=".jsonl,.json,.csv,.tsv,.txt,.zip"
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
              Replace existing entries for this source + language pair
            </label>
          </div>

          <button
            onClick={() => uploadMutation.mutate()}
            disabled={uploadMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
          >
            {uploadMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
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

      {/* Dictionary sources */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-zinc-300 uppercase tracking-wide">
          Dictionary Sources
        </h2>
        {sourcesLoading ? (
          <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
        ) : !sources?.length ? (
          <div className="flex flex-col items-center gap-2 py-10 text-zinc-600">
            <BookOpen className="h-8 w-8" />
            <p className="text-sm">No dictionary sources registered.</p>
          </div>
        ) : (
          <div className="rounded-xl border border-zinc-800 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900">
                  <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Source</th>
                  <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Entries</th>
                  <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Priority</th>
                  <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Status</th>
                  <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-zinc-950">
                {sources.map((s) => <SourceRow key={s.slug} source={s} />)}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Language pairs (collapsible) */}
      <section>
        <button
          onClick={() => setShowPairs((v) => !v)}
          className="flex items-center gap-2 text-sm font-semibold text-zinc-300 uppercase tracking-wide mb-3 hover:text-zinc-100 transition"
        >
          {showPairs ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          Language Pairs
        </button>
        {showPairs && (
          statsLoading ? (
            <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
          ) : !stats?.length ? (
            <p className="text-sm text-zinc-600">No dictionary data loaded yet.</p>
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
          )
        )}
      </section>
    </div>
  )
}
