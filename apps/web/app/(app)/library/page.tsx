"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus } from "lucide-react"
import { listBooks, deleteBook } from "@/src/lib/api/books"
import { BookCard, BookCardSkeleton } from "@/src/components/books/BookCard"
import { ImportBookDialog } from "@/src/components/books/ImportBookDialog"

export default function LibraryPage() {
  const [importOpen, setImportOpen] = useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ["books"],
    queryFn: listBooks,
    refetchInterval: (query) => {
      // Keep polling while any book is processing
      const books = query.state.data?.items ?? []
      return books.some((b) => b.status === "processing" || b.status === "pending")
        ? 5000
        : false
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteBook,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["books"] }),
  })

  const books = data?.items ?? []

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-100">My Library</h1>
        <button
          onClick={() => setImportOpen(true)}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500"
        >
          <Plus className="h-4 w-4" />
          Import Book
        </button>
      </div>

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
            Import an EPUB file to start reading and learning vocabulary.
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
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {books.map((book) => (
            <BookCard
              key={book.id}
              book={book}
              onDelete={(id) => deleteMutation.mutate(id)}
            />
          ))}
        </div>
      )}

      <ImportBookDialog open={importOpen} onClose={() => setImportOpen(false)} />
    </div>
  )
}
