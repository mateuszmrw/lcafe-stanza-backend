"use client"

import { useState } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { Loader2, RefreshCw } from "lucide-react"
import { retokenizeAll } from "@/src/lib/api/admin"
import { listLanguages } from "@/src/lib/api/languages"

export default function AdminStanzaPage() {
  const [languageId, setLanguageId] = useState<string>("")

  const { data: languages = [] } = useQuery({
    queryKey: ["languages"],
    queryFn: listLanguages,
  })

  const retokenize = useMutation({
    mutationFn: () =>
      retokenizeAll(languageId !== "" ? parseInt(languageId, 10) : undefined),
  })

  return (
    <div className="space-y-8">
      <div className="rounded-lg border border-zinc-800 p-6">
        <h2 className="text-lg font-semibold text-zinc-100 mb-1">Re-tokenize pages</h2>
        <p className="text-sm text-zinc-400 mb-6">
          Enqueue tokenization for all ready pages. Use after upgrading Stanza models or enabling
          new processors. Leave language blank to re-tokenize every language.
        </p>

        <div className="flex items-center gap-3 mb-4">
          <select
            value={languageId}
            onChange={(e) => setLanguageId(e.target.value)}
            className="w-56 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All languages</option>
            {languages.map((lang) => (
              <option key={lang.id} value={lang.id}>
                {lang.flag_emoji ? `${lang.flag_emoji} ` : ""}{lang.name} ({lang.code})
              </option>
            ))}
          </select>
          <button
            onClick={() => retokenize.mutate()}
            disabled={retokenize.isPending}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {retokenize.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Re-tokenize
          </button>
        </div>

        {retokenize.isSuccess && (
          <div className="rounded-md bg-green-950 border border-green-800 px-4 py-3 text-sm text-green-300">
            Enqueued {retokenize.data.enqueued} page{retokenize.data.enqueued !== 1 ? "s" : ""} for
            re-tokenization.
          </div>
        )}

        {retokenize.isError && (
          <div className="rounded-md bg-red-950 border border-red-800 px-4 py-3 text-sm text-red-300">
            {retokenize.error instanceof Error
              ? retokenize.error.message
              : "Failed to enqueue re-tokenization."}
          </div>
        )}
      </div>
    </div>
  )
}
