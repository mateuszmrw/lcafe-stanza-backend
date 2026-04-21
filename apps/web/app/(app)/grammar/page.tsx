"use client"

import { useEffect, useState } from "react"
import { GraduationCap, Layers, Link2, Shuffle, Search } from "lucide-react"
import { DrillSessionManager } from "@/src/components/grammar/DrillSessionManager"
import { getAvailableDrills } from "@/src/lib/api/grammar-drills"
import type { AvailableDrill, DrillSessionType } from "@/src/lib/api/grammar-drills"
import { cn } from "@/src/lib/cn"

const DRILL_ICONS: Record<DrillSessionType, React.ReactNode> = {
  form_production: <Layers className="h-5 w-5" />,
  case_identification: <Search className="h-5 w-5" />,
  preposition_case: <Link2 className="h-5 w-5" />,
  aspect_pairs: <Shuffle className="h-5 w-5" />,
}

const UNAVAILABLE_REASONS: Record<string, string> = {
  no_active_language: "Set an active language in Settings.",
  no_form_data: "No data available for your language yet.",
  no_learning_words: "Add words to your learning list first.",
  no_drillable_words: "Not enough drillable words yet.",
}

export default function GrammarPage() {
  const [drills, setDrills] = useState<AvailableDrill[] | null>(null)
  const [active, setActive] = useState<DrillSessionType | null>(null)

  useEffect(() => {
    getAvailableDrills()
      .then((r) => setDrills(r.drills))
      .catch(() => setDrills([]))
  }, [])

  if (active) {
    return (
      <div className="mx-auto max-w-xl px-4 py-10">
        <button
          onClick={() => setActive(null)}
          className="mb-6 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          ← Back to drills
        </button>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
          <DrillSessionManager drillType={active} onBack={() => setActive(null)} />
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <GraduationCap className="h-6 w-6 text-blue-400" />
          <h1 className="text-2xl font-bold text-zinc-100">Grammar Drills</h1>
        </div>
        <p className="text-sm text-zinc-500">
          Practise grammar using your learning vocabulary and real sentences from your books.
        </p>
      </div>

      {drills === null ? (
        <div className="flex justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {drills.map((drill) => (
            <DrillCard
              key={drill.type}
              drill={drill}
              onStart={() => setActive(drill.type)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function DrillCard({ drill, onStart }: { drill: AvailableDrill; onStart: () => void }) {
  const unavailableMessage = drill.reason
    ? (UNAVAILABLE_REASONS[drill.reason] ?? "Not available for your language.")
    : null

  return (
    <div
      className={cn(
        "rounded-xl border p-5 flex flex-col gap-3",
        drill.available
          ? "border-zinc-800 bg-zinc-900"
          : "border-zinc-800/50 bg-zinc-900/50 opacity-60"
      )}
    >
      <div className="flex items-start gap-3">
        <span className={cn("mt-0.5", drill.available ? "text-blue-400" : "text-zinc-600")}>
          {DRILL_ICONS[drill.type]}
        </span>
        <div className="min-w-0">
          <p className="font-semibold text-zinc-100 text-sm">{drill.name}</p>
          <p className="text-xs text-zinc-500 mt-0.5">{drill.description}</p>
        </div>
      </div>

      {drill.available ? (
        <button
          onClick={onStart}
          className="mt-auto rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white
            hover:bg-blue-500 transition-colors"
        >
          Start →
        </button>
      ) : (
        <p className="mt-auto text-xs text-zinc-600">{unavailableMessage}</p>
      )}
    </div>
  )
}
