"use client"

import { useQuery } from "@tanstack/react-query"
import { BookOpen, ChevronRight } from "lucide-react"
import { getBookChapters } from "@/src/lib/api/books"
import { cn } from "@/src/lib/cn"

interface ChapterSidebarProps {
  bookId: string
  currentPage: number
  onPageChange: (page: number) => void
}

export function ChapterSidebar({ bookId, currentPage, onPageChange }: ChapterSidebarProps) {
  const { data: chapters, isLoading } = useQuery({
    queryKey: ["book-chapters", bookId],
    queryFn: () => getBookChapters(bookId),
    staleTime: Infinity,
  })

  return (
    <aside className="flex h-full w-56 flex-col border-r border-zinc-800 bg-zinc-950">
      <div className="flex items-center gap-2 border-b border-zinc-800 px-4 py-3">
        <BookOpen className="h-3.5 w-3.5 text-zinc-500" />
        <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Chapters</span>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {isLoading ? (
          <div className="space-y-1 px-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-8 animate-pulse rounded bg-zinc-800" />
            ))}
          </div>
        ) : chapters && chapters.length > 0 ? (
          <ul>
            {chapters.map((chapter) => {
              const isActive =
                currentPage >= chapter.first_page_number &&
                currentPage < chapter.first_page_number + chapter.page_count

              return (
                <li key={chapter.chapter_number}>
                  <button
                    onClick={() => onPageChange(chapter.first_page_number)}
                    className={cn(
                      "flex w-full items-center gap-2 px-4 py-2 text-left text-sm transition",
                      isActive
                        ? "bg-zinc-800 text-zinc-100"
                        : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200"
                    )}
                  >
                    <ChevronRight
                      className={cn(
                        "h-3 w-3 flex-shrink-0 transition",
                        isActive ? "text-blue-400" : "text-zinc-600"
                      )}
                    />
                    <span className="flex-1 truncate">
                      {chapter.chapter_name ?? `Chapter ${chapter.chapter_number}`}
                    </span>
                    <span className="flex-shrink-0 text-xs text-zinc-600">
                      {chapter.page_count}p
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        ) : (
          <p className="px-4 py-3 text-xs text-zinc-600">No chapters found.</p>
        )}
      </div>
    </aside>
  )
}
