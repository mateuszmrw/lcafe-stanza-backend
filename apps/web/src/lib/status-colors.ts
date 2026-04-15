/** Shared vocabulary status constants used by WordToken and DefinitionPanel. */

export const STATUS_CLASSES: Record<string, string> = {
  new: "bg-sky-500/20 text-sky-200 cursor-pointer hover:bg-sky-500/35",
  learning: "bg-emerald-500/30 text-emerald-100 cursor-pointer hover:bg-emerald-500/45",
  known: "bg-emerald-900/40 text-emerald-300 cursor-pointer hover:bg-emerald-800/55",
  well_known: "text-zinc-400 cursor-pointer hover:bg-zinc-700/50",
  ignored: "text-zinc-600 cursor-pointer hover:bg-zinc-700/30",
}

export const STATUSES = [
  { value: "new", label: "New", color: "bg-sky-700 hover:bg-sky-600" },
  { value: "learning", label: "Learning", color: "bg-emerald-600 hover:bg-emerald-500" },
  { value: "known", label: "Known", color: "bg-emerald-900 hover:bg-emerald-800" },
  { value: "well_known", label: "Well known", color: "bg-zinc-700 hover:bg-zinc-600" },
  { value: "ignored", label: "Ignore", color: "bg-zinc-800 hover:bg-zinc-700 text-zinc-400" },
] as const
