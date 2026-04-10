"use client"

import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"
import { listVocabulary, updateWordStatus, bulkUpdateStatus, type WordResponse } from "@/src/lib/api/vocabulary"
import { listPhrases, updatePhraseStatus, deletePhrase, type PhraseResponse } from "@/src/lib/api/phrases"
import { listLanguages } from "@/src/lib/api/languages"
import { useAuth } from "@/src/stores/auth"
import { Badge } from "@/src/components/ui/Badge"
import { cn } from "@/src/lib/cn"

const STATUS_TABS = [
  { value: undefined, label: "All" },
  { value: "new", label: "New" },
  { value: "learning", label: "Learning" },
  { value: "known", label: "Known" },
  { value: "well_known", label: "Well known" },
  { value: "ignored", label: "Ignored" },
]

const PHRASE_STATUS_TABS = [
  { value: undefined, label: "All" },
  { value: "learning", label: "Learning" },
  { value: "known", label: "Known" },
]

const STATUS_BADGE: Record<string, "blue" | "yellow" | "green" | "zinc"> = {
  new: "blue",
  learning: "yellow",
  known: "green",
  well_known: "green",
  ignored: "zinc",
}

const NEXT_STATUSES = ["new", "learning", "known", "well_known", "ignored"]
const BULK_STATUSES = ["new", "learning", "known", "well_known", "ignored"]

const POS_OPTIONS = [
  { value: "", label: "All POS" },
  { value: "NOUN", label: "Noun" },
  { value: "VERB", label: "Verb" },
  { value: "ADJ", label: "Adjective" },
  { value: "ADV", label: "Adverb" },
  { value: "PROPN", label: "Proper noun" },
  { value: "PRON", label: "Pronoun" },
  { value: "ADP", label: "Adposition" },
  { value: "PART", label: "Particle" },
]

// ─── Words tab ────────────────────────────────────────────────────────────────

function WordsTab({ languageId }: { languageId: number }) {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [posFilter, setPosFilter] = useState("")
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const queryClient = useQueryClient()

  // Reset selection when filters change
  useEffect(() => { setSelected(new Set()) }, [statusFilter, posFilter, page])

  const { data, isLoading } = useQuery({
    queryKey: ["vocabulary", languageId, statusFilter, posFilter, page],
    queryFn: () => listVocabulary(languageId, statusFilter, page, 50, posFilter || undefined),
    enabled: languageId != null,
  })

  const statusMutation = useMutation({
    mutationFn: ({ wordId, status }: { wordId: string; status: string }) =>
      updateWordStatus(wordId, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vocabulary"] }),
  })

  const bulkMutation = useMutation({
    mutationFn: ({ ids, status }: { ids: string[]; status: string }) =>
      bulkUpdateStatus(ids, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vocabulary"] })
      setSelected(new Set())
    },
  })

  function cycleStatus(word: WordResponse) {
    const idx = NEXT_STATUSES.indexOf(word.status)
    const next = NEXT_STATUSES[(idx + 1) % NEXT_STATUSES.length]
    statusMutation.mutate({ wordId: word.id, status: next })
  }

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function toggleSelectAll() {
    const pageIds = (data?.items ?? []).map((w) => w.id)
    const allSelected = pageIds.every((id) => selected.has(id))
    if (allSelected) {
      setSelected((prev) => {
        const next = new Set(prev)
        pageIds.forEach((id) => next.delete(id))
        return next
      })
    } else {
      setSelected((prev) => new Set([...prev, ...pageIds]))
    }
  }

  const words = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / (data?.limit ?? 50))
  const allPageSelected = words.length > 0 && words.every((w) => selected.has(w.id))

  return (
    <>
      {/* Filters row */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex gap-1 border-b border-zinc-800 pb-0">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.label}
              onClick={() => { setStatusFilter(tab.value); setPage(1) }}
              className={cn(
                "rounded-t-md px-4 py-2 text-sm font-medium transition",
                statusFilter === tab.value
                  ? "border-b-2 border-blue-500 text-blue-400"
                  : "text-zinc-500 hover:text-zinc-300"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <select
          value={posFilter}
          onChange={(e) => { setPosFilter(e.target.value); setPage(1) }}
          className="ml-auto rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
        >
          {POS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        {!isLoading && (
          <span className="text-sm text-zinc-500">{total.toLocaleString()} words</span>
        )}
      </div>

      {/* Bulk action bar */}
      {selected.size > 0 && (
        <div className="mb-3 flex items-center gap-3 rounded-lg bg-zinc-800 px-4 py-2">
          <span className="text-sm text-zinc-400">{selected.size} selected</span>
          <select
            defaultValue=""
            onChange={(e) => {
              if (e.target.value) bulkMutation.mutate({ ids: [...selected], status: e.target.value })
              e.target.value = ""
            }}
            disabled={bulkMutation.isPending}
            className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <option value="">Set status…</option>
            {BULK_STATUSES.map((s) => (
              <option key={s} value={s}>{s.replace("_", " ")}</option>
            ))}
          </select>
          <button
            onClick={() => setSelected(new Set())}
            className="ml-auto text-sm text-zinc-500 hover:text-zinc-300 transition"
          >
            Clear
          </button>
        </div>
      )}

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-zinc-800">
        <table className="w-full text-sm">
          <thead className="border-b border-zinc-800 bg-zinc-900">
            <tr>
              <th className="px-3 py-3">
                <input
                  type="checkbox"
                  checked={allPageSelected}
                  onChange={toggleSelectAll}
                  className="h-4 w-4 rounded border-zinc-600 bg-zinc-800 accent-blue-500"
                />
              </th>
              <th className="px-4 py-3 text-left font-medium text-zinc-400">Word</th>
              <th className="px-4 py-3 text-left font-medium text-zinc-400">Lemma</th>
              <th className="px-4 py-3 text-left font-medium text-zinc-400">POS</th>
              <th className="px-4 py-3 text-left font-medium text-zinc-400">Status</th>
              <th className="px-4 py-3 text-left font-medium text-zinc-400">Added</th>
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i} className="animate-pulse border-b border-zinc-800/50">
                    <td className="px-3 py-3"><div className="h-4 w-4 rounded bg-zinc-800" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-24 rounded bg-zinc-800" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 rounded bg-zinc-800" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-12 rounded bg-zinc-800" /></td>
                    <td className="px-4 py-3"><div className="h-5 w-16 rounded-full bg-zinc-800" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 rounded bg-zinc-800" /></td>
                  </tr>
                ))
              : words.map((word) => (
                  <tr
                    key={word.id}
                    className={cn(
                      "border-b border-zinc-800/50 bg-zinc-900 transition hover:bg-zinc-800/50",
                      selected.has(word.id) && "bg-zinc-800/40"
                    )}
                  >
                    <td className="px-3 py-3">
                      <input
                        type="checkbox"
                        checked={selected.has(word.id)}
                        onChange={() => toggleSelect(word.id)}
                        className="h-4 w-4 rounded border-zinc-600 bg-zinc-800 accent-blue-500"
                      />
                    </td>
                    <td className="px-4 py-3 font-medium text-zinc-100">{word.word}</td>
                    <td className="px-4 py-3 text-zinc-400">{word.lemma}</td>
                    <td className="px-4 py-3 text-xs text-zinc-500 uppercase">{word.pos}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => cycleStatus(word)}
                        disabled={statusMutation.isPending}
                        title="Click to cycle status"
                      >
                        <Badge variant={STATUS_BADGE[word.status] ?? "zinc"}>
                          {word.status.replace("_", " ")}
                        </Badge>
                      </button>
                    </td>
                    <td className="px-4 py-3 text-xs text-zinc-500">
                      {new Date(word.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-md px-3 py-1.5 text-sm text-zinc-400 transition hover:bg-zinc-800 disabled:opacity-30"
          >
            ← Prev
          </button>
          <span className="text-sm text-zinc-500">{page} / {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-md px-3 py-1.5 text-sm text-zinc-400 transition hover:bg-zinc-800 disabled:opacity-30"
          >
            Next →
          </button>
        </div>
      )}
    </>
  )
}

// ─── Phrases tab ──────────────────────────────────────────────────────────────

function PhrasesTab({ languageId }: { languageId: number }) {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [page, setPage] = useState(1)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ["phrases", languageId, statusFilter, page],
    queryFn: () => listPhrases(languageId, statusFilter, page),
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      updatePhraseStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["phrases"] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deletePhrase(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["phrases"] }),
  })

  function cycleStatus(phrase: PhraseResponse) {
    const next = phrase.status === "learning" ? "known" : "learning"
    statusMutation.mutate({ id: phrase.id, status: next })
  }

  const phrases = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / (data?.limit ?? 50))

  return (
    <>
      <div className="mb-4 flex items-center gap-1 border-b border-zinc-800 pb-0">
        {PHRASE_STATUS_TABS.map((tab) => (
          <button
            key={tab.label}
            onClick={() => { setStatusFilter(tab.value); setPage(1) }}
            className={cn(
              "rounded-t-md px-4 py-2 text-sm font-medium transition",
              statusFilter === tab.value
                ? "border-b-2 border-blue-500 text-blue-400"
                : "text-zinc-500 hover:text-zinc-300"
            )}
          >
            {tab.label}
          </button>
        ))}
        {!isLoading && (
          <span className="ml-auto self-center pr-1 text-sm text-zinc-500">
            {total.toLocaleString()} phrases
          </span>
        )}
      </div>

      {phrases.length === 0 && !isLoading ? (
        <p className="py-12 text-center text-sm text-zinc-600">
          No phrases saved yet. Select text in the reader and click &quot;Save phrase&quot;.
        </p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-zinc-800">
          <table className="w-full text-sm">
            <thead className="border-b border-zinc-800 bg-zinc-900">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-zinc-400">Phrase</th>
                <th className="px-4 py-3 text-left font-medium text-zinc-400">Translation</th>
                <th className="px-4 py-3 text-left font-medium text-zinc-400">Status</th>
                <th className="px-4 py-3 text-left font-medium text-zinc-400">Saved</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="animate-pulse border-b border-zinc-800/50">
                      <td className="px-4 py-3"><div className="h-4 w-40 rounded bg-zinc-800" /></td>
                      <td className="px-4 py-3"><div className="h-4 w-32 rounded bg-zinc-800" /></td>
                      <td className="px-4 py-3"><div className="h-5 w-16 rounded-full bg-zinc-800" /></td>
                      <td className="px-4 py-3"><div className="h-4 w-20 rounded bg-zinc-800" /></td>
                      <td className="px-4 py-3" />
                    </tr>
                  ))
                : phrases.map((phrase) => (
                    <tr key={phrase.id} className="border-b border-zinc-800/50 bg-zinc-900 hover:bg-zinc-800/50 transition">
                      <td className="px-4 py-3 max-w-xs">
                        <p className="font-medium text-zinc-100 truncate" title={phrase.text}>{phrase.text}</p>
                        {phrase.context && phrase.context !== phrase.text && (
                          <p className="text-xs text-zinc-500 truncate mt-0.5" title={phrase.context}>{phrase.context}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 max-w-xs">
                        <p className="text-zinc-400 truncate" title={phrase.translation ?? ""}>{phrase.translation ?? "—"}</p>
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => cycleStatus(phrase)}
                          disabled={statusMutation.isPending}
                          title="Click to toggle status"
                        >
                          <Badge variant={phrase.status === "known" ? "green" : "yellow"}>
                            {phrase.status}
                          </Badge>
                        </button>
                      </td>
                      <td className="px-4 py-3 text-xs text-zinc-500">
                        {new Date(phrase.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => deleteMutation.mutate(phrase.id)}
                          disabled={deleteMutation.isPending}
                          className="rounded p-1 text-zinc-600 hover:text-red-400 hover:bg-zinc-800 transition"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-2">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}
            className="rounded-md px-3 py-1.5 text-sm text-zinc-400 hover:bg-zinc-800 disabled:opacity-30 transition">
            ← Prev
          </button>
          <span className="text-sm text-zinc-500">{page} / {totalPages}</span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
            className="rounded-md px-3 py-1.5 text-sm text-zinc-400 hover:bg-zinc-800 disabled:opacity-30 transition">
            Next →
          </button>
        </div>
      )}
    </>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function VocabularyPage() {
  const { activeLanguage } = useAuth()
  const [languageId, setLanguageId] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<"words" | "phrases">("words")

  const { data: languages } = useQuery({
    queryKey: ["languages"],
    queryFn: listLanguages,
    staleTime: Infinity,
  })

  useEffect(() => {
    if (languageId !== null) return
    if (activeLanguage) {
      setLanguageId(activeLanguage.id)
    } else if (languages && languages.length > 0) {
      setLanguageId(languages[0].id)
    }
  }, [activeLanguage, languages, languageId])

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-100">Vocabulary</h1>
        <select
          value={languageId ?? ""}
          onChange={(e) => setLanguageId(Number(e.target.value))}
          className="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
        >
          {(languages ?? []).map((l) => (
            <option key={l.id} value={l.id}>
              {l.flag_emoji ? `${l.flag_emoji} ` : ""}{l.name}
            </option>
          ))}
        </select>
      </div>

      {/* Top-level tab: Words / Phrases */}
      <div className="mb-6 flex gap-1 border-b border-zinc-700">
        {(["words", "phrases"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-5 py-2 text-sm font-medium capitalize transition",
              activeTab === tab
                ? "border-b-2 border-blue-500 text-blue-400"
                : "text-zinc-500 hover:text-zinc-300"
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {languageId !== null && (
        activeTab === "words"
          ? <WordsTab languageId={languageId} />
          : <PhrasesTab languageId={languageId} />
      )}
    </div>
  )
}
