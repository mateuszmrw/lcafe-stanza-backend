"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle } from "lucide-react"
import { resetMyData } from "@/src/lib/api/users"

const CONFIRMATION_PHRASE = "DELETE ALL DATA"

export default function DataPage() {
  const [input, setInput] = useState("")
  const [result, setResult] = useState<{ deleted_books: number; deleted_words: number } | null>(null)
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: resetMyData,
    onSuccess: (data) => {
      setResult(data)
      setInput("")
      queryClient.invalidateQueries({ queryKey: ["books"] })
      queryClient.invalidateQueries({ queryKey: ["vocabulary"] })
    },
  })

  const confirmed = input === CONFIRMATION_PHRASE

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-zinc-100">Reset my data</h2>
        <p className="mt-1 text-sm text-zinc-400">
          Permanently deletes all your books, reading progress, and vocabulary. This cannot be undone.
        </p>
      </div>

      <div className="rounded-lg border border-red-900/50 bg-red-950/20 p-4 space-y-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 shrink-0 text-red-400 mt-0.5" />
          <div className="text-sm text-red-300 space-y-1">
            <p className="font-medium">This will delete:</p>
            <ul className="list-disc list-inside text-red-400 space-y-0.5">
              <li>All your imported books and reading progress</li>
              <li>Your entire vocabulary and word statuses</li>
            </ul>
          </div>
        </div>

        <div>
          <label className="block text-sm text-zinc-400 mb-1.5">
            Type <span className="font-mono text-red-400">{CONFIRMATION_PHRASE}</span> to confirm
          </label>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={CONFIRMATION_PHRASE}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 outline-none focus:ring-2 focus:ring-red-500"
          />
        </div>

        <button
          onClick={() => mutation.mutate()}
          disabled={!confirmed || mutation.isPending}
          className="rounded-lg bg-red-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-600 disabled:opacity-40"
        >
          {mutation.isPending ? "Deleting…" : "Delete all my data"}
        </button>

        {mutation.isError && (
          <p className="text-sm text-red-400">{mutation.error.message}</p>
        )}
      </div>

      {result && (
        <div className="rounded-lg bg-zinc-800 px-4 py-3 text-sm text-zinc-300">
          Deleted <span className="text-white font-medium">{result.deleted_books}</span> books
          and <span className="text-white font-medium">{result.deleted_words}</span> vocabulary words.
        </div>
      )}
    </div>
  )
}
