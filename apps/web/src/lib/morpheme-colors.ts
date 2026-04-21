import type { MorphemeRole } from "./morpheme-classifier"

export function getMorphemeColorClass(role: MorphemeRole): string {
  switch (role) {
    case "root":
      return "bg-amber-600/30 text-amber-200 ring-1 ring-amber-600/50"
    case "prefix":
    case "suffix":
      return "bg-zinc-700/60 text-zinc-400"
  }
}
