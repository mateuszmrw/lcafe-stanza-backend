/** Shared vocabulary status constants used by WordToken and DefinitionPanel. */

export const STATUS_CLASSES: Record<string, string> = {
  new: "bg-sky-500/20 text-sky-200 cursor-pointer hover:bg-sky-500/35",
  learning: "bg-emerald-500/30 text-emerald-100 cursor-pointer hover:bg-emerald-500/45",
  known: "bg-emerald-900/40 text-emerald-300 cursor-pointer hover:bg-emerald-800/55",
  well_known: "text-zinc-400 cursor-pointer hover:bg-zinc-700/50",
  ignored: "text-zinc-600 cursor-pointer hover:bg-zinc-700/30",
}

/**
 * Return token class with difficulty-scaled intensity.
 * High difficulty (70-100) = full intensity, medium (30-70) = moderate, low (0-30) = faint.
 * null difficulty = default (current behavior).
 */
const DIFFICULTY_CLASSES: Record<string, Record<string, string>> = {
  new: {
    high: "bg-sky-500/35 text-sky-100 cursor-pointer hover:bg-sky-500/45",
    mid: "bg-sky-500/20 text-sky-200 cursor-pointer hover:bg-sky-500/35",
    low: "bg-sky-500/10 text-sky-300 cursor-pointer hover:bg-sky-500/20",
  },
  learning: {
    high: "bg-emerald-500/40 text-emerald-100 cursor-pointer hover:bg-emerald-500/55",
    mid: "bg-emerald-500/25 text-emerald-200 cursor-pointer hover:bg-emerald-500/40",
    low: "bg-emerald-500/12 text-emerald-300 cursor-pointer hover:bg-emerald-500/25",
  },
}

export function getTokenClass(status: string, difficulty: number | null | undefined): string {
  const tiers = DIFFICULTY_CLASSES[status]
  if (!tiers || difficulty == null) return STATUS_CLASSES[status] ?? STATUS_CLASSES.new
  if (difficulty >= 70) return tiers.high
  if (difficulty >= 30) return tiers.mid
  return tiers.low
}

export const STATUSES = [
  { value: "new", label: "New", color: "bg-sky-700 hover:bg-sky-600" },
  { value: "learning", label: "Learning", color: "bg-emerald-600 hover:bg-emerald-500" },
  { value: "known", label: "Known", color: "bg-emerald-900 hover:bg-emerald-800" },
  { value: "well_known", label: "Well known", color: "bg-zinc-700 hover:bg-zinc-600" },
  { value: "ignored", label: "Ignore", color: "bg-zinc-800 hover:bg-zinc-700 text-zinc-400" },
] as const
