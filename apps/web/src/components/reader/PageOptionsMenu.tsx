"use client"

import { useEffect, useRef, useState } from "react"
import { SlidersHorizontal, BookCheck } from "lucide-react"
import { cn } from "@/src/lib/cn"
import {
  useReaderSettings,
  type FontSize,
  type LineSpacing,
  type TextWidth,
} from "@/src/stores/readerSettings"

interface PageOptionsMenuProps {}

function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[]
  value: T
  onChange: (v: T) => void
}) {
  return (
    <div className="flex rounded-lg border border-zinc-700 bg-zinc-800 p-0.5 gap-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            "flex-1 rounded px-2 py-1 text-xs transition",
            value === o.value
              ? "bg-zinc-600 text-zinc-100"
              : "text-zinc-400 hover:text-zinc-200"
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function PageOptionsMenu({}: PageOptionsMenuProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const { fontSize, lineSpacing, textWidth, autoMarkRead, setFontSize, setLineSpacing, setTextWidth, setAutoMarkRead } =
    useReaderSettings()

  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        title="Page options"
        className={cn(
          "rounded-lg p-1.5 transition hover:bg-zinc-800",
          open && "bg-zinc-800",
          autoMarkRead ? "text-emerald-400 hover:text-emerald-300" : "text-zinc-400 hover:text-zinc-200"
        )}
      >
        <SlidersHorizontal className="h-4 w-4" />
      </button>

      {open && (
        <div className="absolute bottom-full right-0 mb-2 w-60 rounded-xl border border-zinc-700 bg-zinc-900 p-4 shadow-xl space-y-4 z-50">
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
              Font size
            </p>
            <SegmentedControl<FontSize>
              options={[
                { value: "sm", label: "S" },
                { value: "md", label: "M" },
                { value: "lg", label: "L" },
                { value: "xl", label: "XL" },
              ]}
              value={fontSize}
              onChange={setFontSize}
            />
          </div>

          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
              Line spacing
            </p>
            <SegmentedControl<LineSpacing>
              options={[
                { value: "tight", label: "Tight" },
                { value: "normal", label: "Normal" },
                { value: "relaxed", label: "Relaxed" },
              ]}
              value={lineSpacing}
              onChange={setLineSpacing}
            />
          </div>

          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
              Text width
            </p>
            <SegmentedControl<TextWidth>
              options={[
                { value: "narrow", label: "Narrow" },
                { value: "reading", label: "Reading" },
                { value: "wide", label: "Wide" },
                { value: "full", label: "Full" },
              ]}
              value={textWidth}
              onChange={setTextWidth}
            />
          </div>

          <div className="border-t border-zinc-800" />
          <button
            onClick={() => setAutoMarkRead(!autoMarkRead)}
            className={cn(
              "flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition",
              autoMarkRead
                ? "text-emerald-400 hover:bg-zinc-800"
                : "text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
            )}
          >
            Mark page as read
            <BookCheck className={cn("h-3.5 w-3.5", autoMarkRead ? "text-emerald-400" : "text-zinc-500")} />
          </button>
        </div>
      )}
    </div>
  )
}
