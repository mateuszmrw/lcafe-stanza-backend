"use client"

import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { listVocabulary, updateWordStatus, type WordResponse } from "@/src/lib/api/vocabulary"
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

const STATUS_BADGE: Record<string, "blue" | "yellow" | "green" | "zinc"> = {
  new: "blue",
  learning: "yellow",
  known: "green",
  well_known: "green",
  ignored: "zinc",
}

const NEXT_STATUSES = ["new", "learning", "known", "well_known", "ignored"]

export default function VocabularyPage() {
  const { activeLanguage } = useAuth()
  const [languageId, setLanguageId] = useState<number | null>(null)
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [page, setPage] = useState(1)
  const queryClient = useQueryClient()

  const { data: languages } = useQuery({
    queryKey: ["languages"],
    queryFn: listLanguages,
    staleTime: Infinity,
  })

  // Default to active language once languages load
  useEffect(() => {
    if (languageId !== null) return
    if (activeLanguage) {
      setLanguageId(activeLanguage.id)
    } else if (languages && languages.length > 0) {
      setLanguageId(languages[0].id)
    }
  }, [activeLanguage, languages, languageId])

  const { data, isLoading } = useQuery({
    queryKey: ["vocabulary", languageId, statusFilter, page],
    queryFn: () => listVocabulary(languageId!, statusFilter, page),
    enabled: languageId !== null,
  })

  const statusMutation = useMutation({
    mutationFn: ({ wordId, status }: { wordId: string; status: string }) =>
      updateWordStatus(wordId, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vocabulary"] }),
  })

  function cycleStatus(word: WordResponse) {
    const idx = NEXT_STATUSES.indexOf(word.status)
    const next = NEXT_STATUSES[(idx + 1) % NEXT_STATUSES.length]
    statusMutation.mutate({ wordId: word.id, status: next })
  }

  const words = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / (data?.limit ?? 50))

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-100">Vocabulary</h1>
        <select
          value={languageId ?? ""}
          onChange={(e) => { setLanguageId(Number(e.target.value)); setPage(1) }}
          className="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
        >
          {(languages ?? []).map((l) => (
            <option key={l.id} value={l.id}>
              {l.flag_emoji ? `${l.flag_emoji} ` : ""}{l.name}
            </option>
          ))}
        </select>
      </div>

      {/* Status tabs */}
      <div className="mb-4 flex gap-1 border-b border-zinc-800 pb-0">
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
        {!isLoading && (
          <span className="ml-auto self-center pr-1 text-sm text-zinc-500">
            {total.toLocaleString()} words
          </span>
        )}
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-zinc-800">
        <table className="w-full text-sm">
          <thead className="border-b border-zinc-800 bg-zinc-900">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-zinc-400">Word</th>
              <th className="px-4 py-3 text-left font-medium text-zinc-400">Lemma</th>
              <th className="px-4 py-3 text-left font-medium text-zinc-400">POS</th>
              <th className="px-4 py-3 text-left font-medium text-zinc-400">Status</th>
              <th className="px-4 py-3 text-left font-medium text-zinc-400">Added</th>
            </tr>
          </thead>
          <tbody>
            {isLoading || languageId === null
              ? Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i} className="animate-pulse border-b border-zinc-800/50">
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
                    className="border-b border-zinc-800/50 bg-zinc-900 transition hover:bg-zinc-800/50"
                  >
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
    </div>
  )
}
