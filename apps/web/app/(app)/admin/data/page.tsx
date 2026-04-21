"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Trash2, AlertTriangle } from "lucide-react"
import { resetAllData, resetActivity } from "@/src/lib/api/admin-data"

const REQUIRED_PHRASE = "DELETE ALL DATA"

export default function DataPage() {
  const [input, setInput] = useState("")
  const queryClient = useQueryClient()

  const { mutate, isPending, isSuccess, data, error } = useMutation({
    mutationFn: () => resetAllData(input),
    onSuccess: () => {
      setInput("")
      queryClient.removeQueries({ queryKey: ["stats"] })
      queryClient.removeQueries({ queryKey: ["vocabulary"] })
      queryClient.removeQueries({ queryKey: ["books"] })
    },
  })

  const {
    mutate: mutateActivity,
    isPending: isActivityPending,
    isSuccess: isActivitySuccess,
  } = useMutation({
    mutationFn: resetActivity,
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["stats"] })
      queryClient.removeQueries({ queryKey: ["activity"] })
    },
  })

  const confirmed = input === REQUIRED_PHRASE

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-zinc-100">Data Management</h2>
        <p className="mt-1 text-sm text-zinc-400">
          Permanently delete all content from the application.
        </p>
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6 space-y-4">
        <div className="flex items-start gap-3">
          <Trash2 className="mt-0.5 h-5 w-5 shrink-0 text-zinc-400" />
          <div>
            <h3 className="font-medium text-zinc-100">Reset activity data</h3>
            <p className="mt-1 text-sm text-zinc-400">
              Wipe all reading streaks and page-read counts for all users. Useful after fixing
              counting bugs. Cannot be undone.
            </p>
          </div>
        </div>
        {isActivitySuccess && (
          <div className="rounded-md border border-green-800/50 bg-green-950/30 px-4 py-3 text-sm text-green-300">
            Activity data cleared.
          </div>
        )}
        <button
          onClick={() => mutateActivity()}
          disabled={isActivityPending}
          className="flex items-center gap-2 rounded-md bg-zinc-700 px-4 py-2 text-sm font-medium text-zinc-100 transition hover:bg-zinc-600 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Trash2 className="h-4 w-4" />
          {isActivityPending ? "Clearing…" : "Clear activity data"}
        </button>
      </div>

      <div className="rounded-lg border border-red-900/50 bg-red-950/20 p-6 space-y-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" />
          <div>
            <h3 className="font-medium text-red-300">Reset all data</h3>
            <p className="mt-1 text-sm text-zinc-400">
              This will permanently delete:
            </p>
            <ul className="mt-2 space-y-0.5 text-sm text-zinc-400 list-disc list-inside">
              <li>All uploaded books and their pages</li>
              <li>All tokenized page content</li>
              <li>All vocabulary words and their statuses</li>
              <li>All book files stored on disk</li>
            </ul>
            <p className="mt-3 text-sm font-medium text-red-400">
              This action cannot be undone.
            </p>
          </div>
        </div>

        {isSuccess && data && (
          <div className="rounded-md border border-green-800/50 bg-green-950/30 px-4 py-3 text-sm text-green-300">
            Deleted {data.deleted_books} book{data.deleted_books !== 1 ? "s" : ""} and{" "}
            {data.deleted_words} vocabulary word{data.deleted_words !== 1 ? "s" : ""}.
          </div>
        )}

        {error && (
          <div className="rounded-md border border-red-800/50 bg-red-950/30 px-4 py-3 text-sm text-red-300">
            {error instanceof Error ? error.message : "Something went wrong."}
          </div>
        )}

        <div className="space-y-2">
          <label className="block text-sm text-zinc-300">
            Type{" "}
            <code className="rounded bg-zinc-800 px-1.5 py-0.5 text-xs font-mono text-zinc-200">
              {REQUIRED_PHRASE}
            </code>{" "}
            to confirm:
          </label>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={REQUIRED_PHRASE}
            className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:border-red-600 focus:outline-none focus:ring-1 focus:ring-red-600"
          />
        </div>

        <button
          onClick={() => mutate()}
          disabled={!confirmed || isPending}
          className="flex items-center gap-2 rounded-md bg-red-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-600 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Trash2 className="h-4 w-4" />
          {isPending ? "Deleting…" : "Delete all data"}
        </button>
      </div>
    </div>
  )
}
