"use client"

import { useQuery } from "@tanstack/react-query"
import { useEffect, useMemo, useRef, useState } from "react"
import { getMorphemeFamily, type WordFamilyItem } from "@/src/lib/api/vocabulary"
import { lookup } from "@/src/lib/api/dictionary"
import { STATUS_CLASSES } from "@/src/lib/status-colors"
import type { MorphemeRole } from "@/src/lib/morpheme-classifier"
import { cn } from "@/src/lib/cn"

interface MorphemePopoverProps {
  morpheme: string
  languageId: number
  sourceLang: string
  role: MorphemeRole
  colorClass: string
  onWordClick?: (word: string) => void
}

export function MorphemePopover({ morpheme, languageId, sourceLang, role, colorClass, onWordClick }: MorphemePopoverProps) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const isRoot = role === "root"

  const { data: familyData, isLoading: familyLoading } = useQuery({
    queryKey: ["morpheme-family", morpheme, languageId, sourceLang],
    queryFn: () => getMorphemeFamily(morpheme, languageId, sourceLang),
    enabled: open,
    staleTime: 5 * 60 * 1000,
  })

  const { data: dictData, isLoading: dictLoading } = useQuery({
    queryKey: ["morpheme-dict", morpheme, sourceLang],
    queryFn: () => lookup(morpheme, sourceLang, "en"),
    enabled: open && isRoot,
    staleTime: Infinity,
  })

  const glosses = useMemo(() => {
    const out: string[] = []
    for (const group of (dictData?.results ?? [])) {
      for (const entry of group.entries) {
        for (const g of entry.glosses) {
          if (!out.includes(g)) out.push(g)
          if (out.length >= 2) return out
        }
      }
    }
    return out
  }, [dictData])

  useEffect(() => {
    if (!open) return
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [open])

  const results = familyData?.results ?? []

  return (
    <div ref={containerRef} className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "rounded px-1.5 py-0.5 text-xs font-mono transition hover:opacity-80 cursor-pointer",
          colorClass,
        )}
      >
        {morpheme}
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 min-w-[160px] max-w-[240px] rounded-lg border border-zinc-700 bg-zinc-900 p-2 shadow-xl">
          {/* Dictionary meaning — roots only */}
          {isRoot && (
            <div className="mb-2 pb-2 border-b border-zinc-800">
              <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-zinc-500">
                Meaning
              </p>
              {dictLoading && (
                <p className="text-xs text-zinc-500">…</p>
              )}
              {!dictLoading && glosses.length === 0 && (
                <p className="text-xs text-zinc-600">No entry found</p>
              )}
              {!dictLoading && glosses.map((g, i) => (
                <p key={i} className="text-xs text-zinc-300 leading-snug">{g}</p>
              ))}
            </div>
          )}

          {/* Word family */}
          <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-zinc-500">
            Words with <span className="text-zinc-300">–{morpheme}–</span>
          </p>
          {familyLoading && (
            <p className="text-xs text-zinc-500 py-1">Loading…</p>
          )}
          {!familyLoading && results.length === 0 && (
            <p className="text-xs text-zinc-500 py-1">No matches</p>
          )}
          {!familyLoading && results.length > 0 && (
            <ul className="space-y-0.5">
              {results.map((item: WordFamilyItem) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => {
                      onWordClick?.(item.word)
                      setOpen(false)
                    }}
                    className="flex w-full items-start justify-between gap-2 rounded px-1 py-0.5 text-left text-xs hover:bg-zinc-800"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="font-mono text-zinc-200">{item.word}</span>
                      {item.translation && (
                        <span className="block truncate text-[10px] text-zinc-500 leading-tight">{item.translation}</span>
                      )}
                    </span>
                    <span
                      className={cn(
                        "mt-0.5 shrink-0 rounded px-1 text-[10px]",
                        STATUS_CLASSES[item.status] ?? "text-zinc-500",
                      )}
                    >
                      {item.status.replace("_", " ")}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
