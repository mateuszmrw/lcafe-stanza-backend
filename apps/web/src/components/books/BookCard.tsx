"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { MoreVertical, Trash2 } from "lucide-react"
import type { BookListItem } from "@/src/lib/api/books"
import { Badge } from "@/src/components/ui/Badge"
import { Spinner } from "@/src/components/ui/Spinner"
import { cn } from "@/src/lib/cn"

const STATUS_BADGE: Record<
  string,
  { variant: "zinc" | "blue" | "green" | "red"; label: string }
> = {
  pending: { variant: "zinc", label: "Pending" },
  processing: { variant: "blue", label: "Processing" },
  completed: { variant: "green", label: "Completed" },
  failed: { variant: "red", label: "Failed" },
}

interface BookCardProps {
  book: BookListItem
  onDelete: (id: string) => void
}

export function BookCard({ book, onDelete }: BookCardProps) {
  const router = useRouter()
  const [menuOpen, setMenuOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const badge = STATUS_BADGE[book.status] ?? { variant: "zinc" as const, label: book.status }
  const initials = book.title
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("")

  const isReadable = book.status === "completed" || book.status === "processing"

  function handleCardClick() {
    if (isReadable) router.push(`/reader/${book.id}`)
  }

  return (
    <div
      className={cn(
        "group relative flex flex-col rounded-xl border border-zinc-800 bg-zinc-900 p-5 transition",
        isReadable
          ? "cursor-pointer hover:border-zinc-600 hover:bg-zinc-800"
          : "cursor-default opacity-80"
      )}
      onClick={handleCardClick}
    >
      {/* Cover placeholder */}
      <div className="mb-4 flex h-32 w-full items-center justify-center rounded-lg bg-zinc-800 text-2xl font-bold text-zinc-500">
        {initials || "?"}
      </div>

      {/* Title */}
      <h3 className="mb-2 line-clamp-2 text-sm font-semibold text-zinc-100">
        {book.title}
      </h3>

      {/* Coverage bar */}
      {book.status === "completed" && book.coverage_pct != null && (
        <div className="mb-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-zinc-400">You know {book.coverage_pct}%</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-zinc-800">
            <div
              className="h-full rounded-full bg-emerald-500/70 transition-all duration-500"
              style={{ width: `${book.coverage_pct}%` }}
            />
          </div>
        </div>
      )}

      <div className="mt-auto flex items-center justify-between pt-2">
        <div className="flex items-center gap-2">
          <Badge variant={badge.variant}>{badge.label}</Badge>
          {book.status === "processing" && (
            <Spinner className="h-3 w-3 text-blue-400" />
          )}
        </div>
        {book.word_count != null && (
          <span className="text-xs text-zinc-500">{book.word_count.toLocaleString()} words</span>
        )}
      </div>

      {/* Three-dot menu */}
      <div
        className="absolute right-3 top-3"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={() => setMenuOpen((v) => !v)}
          aria-label="Book options"
          className="rounded-md p-1 text-zinc-500 opacity-0 transition group-hover:opacity-100 hover:bg-zinc-700 hover:text-zinc-100"
        >
          <MoreVertical className="h-4 w-4" />
        </button>
        {menuOpen && (
          <div className="absolute right-0 top-8 z-10 min-w-[120px] rounded-lg border border-zinc-700 bg-zinc-800 py-1 shadow-xl">
            {!confirmDelete ? (
              <button
                onClick={() => setConfirmDelete(true)}
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-400 transition hover:bg-zinc-700"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </button>
            ) : (
              <div className="px-3 py-2">
                <p className="mb-2 text-xs text-zinc-400">Delete this book?</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => { onDelete(book.id); setMenuOpen(false) }}
                    className="rounded bg-red-600 px-2 py-1 text-xs text-white hover:bg-red-500"
                  >
                    Yes
                  </button>
                  <button
                    onClick={() => { setConfirmDelete(false); setMenuOpen(false) }}
                    className="rounded bg-zinc-700 px-2 py-1 text-xs text-zinc-300 hover:bg-zinc-600"
                  >
                    No
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export function BookCardSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border border-zinc-800 bg-zinc-900 p-5">
      <div className="mb-4 h-32 w-full rounded-lg bg-zinc-800" />
      <div className="mb-2 h-4 w-3/4 rounded bg-zinc-800" />
      <div className="h-3 w-1/2 rounded bg-zinc-800" />
    </div>
  )
}
