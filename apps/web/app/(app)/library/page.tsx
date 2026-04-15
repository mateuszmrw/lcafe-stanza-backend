"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Search, X } from "lucide-react"
import { listBooks, deleteBook } from "@/src/lib/api/books"
import { getStats } from "@/src/lib/api/stats"
import { getStreak } from "@/src/lib/api/activity"
import { BookCard, BookCardSkeleton } from "@/src/components/books/BookCard"
import { ImportBookDialog } from "@/src/components/books/ImportBookDialog"
import { useAuth } from "@/src/stores/auth"

function StatsBar() {
  const { activeLanguage } = useAuth()
  const { data: stats } = useQuery({
    queryKey: ["stats", activeLanguage?.code],
    queryFn: () => getStats(activeLanguage!.code),
    enabled: Boolean(activeLanguage?.code),
    staleTime: 60_000,
  })
  const { data: streak } = useQuery({
    queryKey: ["streak", activeLanguage?.id],
    queryFn: () => getStreak(activeLanguage!.id),
    enabled: Boolean(activeLanguage?.id),
    staleTime: 60_000,
  })

  if (!stats) return null

  const known = (stats.word_counts.known ?? 0) + (stats.word_counts.well_known ?? 0)
  const learning = stats.word_counts.learning ?? 0
  const total = Object.values(stats.word_counts).reduce((a, b) => a + b, 0)
  const cov1k = stats.frequency_coverage.top_1k
  const cov5k = stats.frequency_coverage.top_5k

  return (
    <div className="mb-6 flex flex-wrap items-center gap-4 rounded-xl border border-zinc-800 bg-zinc-900 px-5 py-3 text-sm">
      <span className="text-zinc-500 font-medium">{activeLanguage?.name}</span>
      <div className="flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-emerald-400" />
        <span className="text-zinc-300">{known.toLocaleString()} known</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-sky-400" />
        <span className="text-zinc-300">{learning.toLocaleString()} learning</span>
      </div>
      <span className="text-zinc-600">{total.toLocaleString()} total</span>
      {cov1k != null && (
        <span className="text-zinc-500">
          Top 1k: <span className="text-zinc-300">{Math.round(cov1k * 100)}%</span>
        </span>
      )}
      {cov5k != null && (
        <span className="text-zinc-500">
          Top 5k: <span className="text-zinc-300">{Math.round(cov5k * 100)}%</span>
        </span>
      )}
      {streak && streak.current_streak > 0 && (
        <div className="ml-auto flex items-center gap-1.5">
          <span title={`Longest streak: ${streak.longest_streak} days`}>
            🔥 <span className="text-zinc-300">{streak.current_streak} day streak</span>
          </span>
        </div>
      )}
    </div>
  )
}

export default function LibraryPage() {
  const [importOpen, setImportOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ["books"],
    queryFn: listBooks,
    refetchInterval: (query) => {
      // Keep polling while any book is processing
      const books = query.state.data?.items ?? []
      return books.some((b) => b.status === "processing" || b.status === "pending")
        ? 2000
        : false
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteBook,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["books"] }),
  })

  const books = data?.items ?? []
  const filteredBooks = searchTerm
    ? books.filter((b) => b.title.toLowerCase().includes(searchTerm.toLowerCase()))
    : books

  return (
    <div className="p-8">
      <StatsBar />
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-100">My Library</h1>
        <button
          onClick={() => setImportOpen(true)}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500"
        >
          <Plus className="h-4 w-4" />
          Import Book
        </button>
      </div>

      {/* Search */}
      {books.length > 0 && (
        <div className="relative mb-6 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-500 pointer-events-none" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search books…"
            className="w-full rounded-lg border border-zinc-700 bg-zinc-800 pl-8 pr-8 py-1.5 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-zinc-500 hover:text-zinc-300"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <BookCardSkeleton key={i} />
          ))}
        </div>
      ) : books.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="mb-4 text-5xl">📚</div>
          <h2 className="mb-2 text-lg font-semibold text-zinc-300">
            Your library is empty
          </h2>
          <p className="mb-6 text-sm text-zinc-500">
            Import an EPUB, PDF, or YouTube video to start reading and learning vocabulary.
          </p>
          <button
            onClick={() => setImportOpen(true)}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500"
          >
            <Plus className="h-4 w-4" />
            Import your first book
          </button>
        </div>
      ) : (
        <>
          {filteredBooks.length === 0 && searchTerm ? (
            <p className="py-12 text-center text-sm text-zinc-600">
              No books matching &ldquo;{searchTerm}&rdquo;
            </p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {filteredBooks.map((book) => (
                <BookCard
                  key={book.id}
                  book={book}
                  onDelete={(id) => deleteMutation.mutate(id)}
                />
              ))}
            </div>
          )}
        </>
      )}

      <ImportBookDialog open={importOpen} onClose={() => setImportOpen(false)} />
    </div>
  )
}
