"use client"

import type { DictionaryEntry, FrequencyInfo } from "@/src/lib/api/dictionary"
import { cn } from "@/src/lib/cn"
import { FormsTable } from "./FormsTable"

export const POS_LABELS: Record<string, string> = {
  ADJ: "Adjective", ADP: "Adposition", ADV: "Adverb", AUX: "Auxiliary",
  CCONJ: "Coord. Conjunction", DET: "Determiner", INTJ: "Interjection",
  NOUN: "Noun", NUM: "Numeral", PART: "Particle", PRON: "Pronoun",
  PROPN: "Proper Noun", PUNCT: "Punctuation", SCONJ: "Subord. Conjunction",
  SYM: "Symbol", VERB: "Verb", X: "Other",
}

export const LABEL_CLASSES: Record<string, string> = {
  informal:    "bg-amber-900/60 text-amber-300",
  colloquial:  "bg-amber-900/60 text-amber-300",
  slang:       "bg-amber-900/60 text-amber-300",
  formal:      "bg-blue-900/60 text-blue-300",
  literary:    "bg-blue-900/60 text-blue-300",
  poetic:      "bg-blue-900/60 text-blue-300",
  archaic:     "bg-purple-900/60 text-purple-300",
  obsolete:    "bg-purple-900/60 text-purple-300",
  dated:       "bg-purple-900/60 text-purple-300",
  historical:  "bg-purple-900/60 text-purple-300",
  regional:    "bg-emerald-900/60 text-emerald-300",
  dialectal:   "bg-emerald-900/60 text-emerald-300",
  vulgar:      "bg-red-900/60 text-red-300",
  offensive:   "bg-red-900/60 text-red-300",
  derogatory:  "bg-red-900/60 text-red-300",
  technical:   "bg-indigo-900/60 text-indigo-300",
  rare:        "bg-zinc-700/60 text-zinc-400",
}

const FREQ_TIER_CLASSES: Record<string, string> = {
  very_common: "bg-green-900/60 text-green-300",
  common:      "bg-sky-900/60 text-sky-300",
  uncommon:    "bg-yellow-900/60 text-yellow-300",
  rare:        "bg-zinc-700/60 text-zinc-400",
  very_rare:   "bg-zinc-800/60 text-zinc-600",
}

const FREQ_TIER_LABELS: Record<string, string> = {
  very_common: "Very common",
  common:      "Common",
  uncommon:    "Uncommon",
  rare:        "Rare",
  very_rare:   "Very rare",
}

const TONE_CLASSES: Record<string, string> = {
  "1": "text-sky-300",
  "2": "text-green-400",
  "3": "text-amber-400",
  "4": "text-red-400",
  "5": "text-zinc-400",
}

const KRDICT_LEVEL_CLASSES: Record<string, string> = {
  beginner:     "bg-emerald-900/50 text-emerald-400",
  intermediate: "bg-sky-900/50 text-sky-400",
  advanced:     "bg-violet-900/50 text-violet-400",
}

export function FrequencyBadge({ freq }: { freq: FrequencyInfo }) {
  const cls = FREQ_TIER_CLASSES[freq.tier] ?? "bg-zinc-700/60 text-zinc-400"
  const label = FREQ_TIER_LABELS[freq.tier] ?? freq.tier
  return (
    <span className={cn("inline-block rounded px-1.5 py-0.5 text-xs", cls)}>
      {label} <span className="opacity-60">#{freq.rank}</span>
    </span>
  )
}

function PinyinDisplay({ pinyin }: { pinyin: string }) {
  const syllables = pinyin.split(" ").filter(Boolean)
  return (
    <span className="font-mono text-sm tracking-wide">
      {syllables.map((syl, i) => {
        const tone = syl.match(/(\d)$/)?.[1] ?? "5"
        const text = syl.replace(/\d$/, "")
        return (
          <span key={i}>
            <span className={TONE_CLASSES[tone] ?? "text-zinc-400"}>{text}</span>
            <sup className="text-[9px] opacity-50 mr-0.5">{tone !== "5" ? tone : ""}</sup>
          </span>
        )
      })}
    </span>
  )
}

export function CcCedictEntryCard({ entry, index }: { entry: DictionaryEntry; index: number }) {
  const meta = entry.metadata ?? {}
  const traditional = meta.traditional as string | undefined
  const pinyin = meta.pinyin as string | undefined
  const showTraditional = traditional && traditional !== entry.lemma

  return (
    <div className="rounded-lg bg-zinc-800 p-3 border-l-2 border-orange-700/60">
      <div className="mb-1.5 flex flex-wrap items-center gap-2">
        {showTraditional && (
          <span className="text-sm text-zinc-400">
            <span className="text-zinc-500 text-xs mr-0.5">繁</span>
            {traditional}
          </span>
        )}
        {pinyin && <PinyinDisplay pinyin={pinyin} />}
        {index === 0 && entry.frequency && <FrequencyBadge freq={entry.frequency} />}
      </div>
      <div className="space-y-1">
        {entry.glosses.slice(0, 5).map((gloss, j) => (
          <p key={j} className="text-sm text-zinc-200">{j + 1}. {gloss}</p>
        ))}
      </div>
    </div>
  )
}

type KrdictDefinition = {
  text: string
  en?: string | null
  en_def?: string | null
  examples?: string[]
}

export function KrdictEntryCard({ entry, index }: { entry: DictionaryEntry; index: number }) {
  const meta = entry.metadata ?? {}
  const hanja = meta.hanja as string | undefined
  const level = meta.level as string | undefined
  const definitions = (meta.definitions ?? []) as KrdictDefinition[]

  return (
    <div className="rounded-lg bg-zinc-800 p-3 border-l-2 border-rose-700/60">
      <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
        {hanja && <span className="text-sm font-medium text-zinc-300">{hanja}</span>}
        {entry.pos && <span className="text-xs font-medium text-zinc-400 uppercase">{entry.pos}</span>}
        {level && (
          <span className={cn(
            "inline-block rounded px-1.5 py-0.5 text-xs capitalize",
            KRDICT_LEVEL_CLASSES[level] ?? "bg-zinc-700/60 text-zinc-400"
          )}>
            {level}
          </span>
        )}
        {index === 0 && entry.frequency && <FrequencyBadge freq={entry.frequency} />}
      </div>
      <div className="space-y-2">
        {definitions.slice(0, 4).map((defn, j) => (
          <div key={j}>
            {defn.en ? (
              <p className="text-sm text-zinc-200">{j + 1}. {defn.en}</p>
            ) : (
              <p className="text-sm text-zinc-200">{j + 1}. {defn.text}</p>
            )}
            {defn.examples && defn.examples.length > 0 && (
              <div className="mt-1 pl-3 border-l border-zinc-700/60">
                <p className="text-xs text-zinc-400">{defn.examples[0]}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export function DictCcEntryCard({ entry, index }: { entry: DictionaryEntry; index: number }) {
  const meta = entry.metadata ?? {}
  const notes = meta.notes as string | undefined

  return (
    <div className="rounded-lg bg-zinc-800 p-3 border-l-2 border-emerald-700/60">
      <div className="mb-1 flex flex-wrap items-center gap-1.5">
        {entry.pos && <span className="text-xs font-medium text-zinc-400 uppercase">{entry.pos}</span>}
        {notes && <span className="text-xs text-zinc-500 italic">{notes}</span>}
        {index === 0 && entry.frequency && <FrequencyBadge freq={entry.frequency} />}
      </div>
      <p className="text-sm text-zinc-200">{entry.glosses[0]}</p>
    </div>
  )
}

type OpenRussianExample = { ru: string; en?: string }

export function OpenRussianEntryCard({
  entry,
  index,
  activeCase,
}: {
  entry: DictionaryEntry
  index: number
  activeCase?: string
}) {
  const meta = entry.metadata ?? {}
  const accented = meta.accented as string | undefined
  const aspect = meta.aspect as string | undefined
  const examples = (meta.examples ?? []) as OpenRussianExample[]

  return (
    <div className="rounded-lg bg-zinc-800 p-3 border-l-2 border-teal-700/60">
      <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
        {accented && (
          <span className="text-base font-bold text-teal-300 mr-0.5 tracking-wide">{accented}</span>
        )}
        <span className="text-xs font-medium text-zinc-400 uppercase">
          {POS_LABELS[entry.pos] ?? entry.pos}
        </span>
        {aspect && (
          <span className="inline-block rounded px-1.5 py-0.5 text-xs bg-sky-900/50 text-sky-400 capitalize">
            {aspect}
          </span>
        )}
        {entry.labels?.filter(l => l !== aspect).map((label) => (
          <span
            key={label}
            className={cn(
              "inline-block rounded px-1.5 py-0.5 text-xs capitalize",
              LABEL_CLASSES[label] ?? "bg-zinc-700/60 text-zinc-400"
            )}
          >
            {label}
          </span>
        ))}
        {index === 0 && entry.frequency && <FrequencyBadge freq={entry.frequency} />}
      </div>
      <div className="space-y-2">
        {entry.glosses.slice(0, 4).map((gloss, j) => {
          const example = examples[j]
          return (
            <div key={j}>
              <p className="text-sm text-zinc-200">{j + 1}. {gloss}</p>
              {example?.ru && (
                <div className="mt-1 pl-3 border-l border-zinc-700/60 space-y-0.5">
                  <p className="text-xs text-zinc-400">{example.ru}</p>
                  {example.en && <p className="text-xs text-zinc-500 italic">{example.en}</p>}
                </div>
              )}
            </div>
          )
        })}
      </div>
      {entry.forms && entry.forms.length > 0 && (
        <div className="mt-2.5 pt-2 border-t border-zinc-700/40">
          <FormsTable forms={entry.forms} activeCase={activeCase} />
        </div>
      )}
    </div>
  )
}
