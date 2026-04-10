"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect } from "react"
import { X, Loader2, AlertTriangle, ArrowLeft, BrainCircuit } from "lucide-react"
import type { PageListResponse, TokenWithStatus } from "@/src/lib/api/books"
import { upsertWordStatus } from "@/src/lib/api/vocabulary"
import { translate, getTranslationAvailable } from "@/src/lib/api/translation"
import { lookup, type FrequencyInfo } from "@/src/lib/api/dictionary"
import { explainGrammar, type GrammarExplainResponse } from "@/src/lib/api/grammar"
import { useReaderStore } from "@/src/stores/reader"
import { getLanguageLabel } from "@/src/lib/language-flags"
import { cn } from "@/src/lib/cn"

const MAX_SELECTION_CHARS = 500

const STATUSES = [
  { value: "new", label: "New", color: "bg-blue-600 hover:bg-blue-500" },
  { value: "learning", label: "Learning", color: "bg-yellow-600 hover:bg-yellow-500" },
  { value: "known", label: "Known", color: "bg-green-700 hover:bg-green-600" },
  { value: "well_known", label: "Well known", color: "bg-green-900 hover:bg-green-800" },
  { value: "ignored", label: "Ignore", color: "bg-zinc-700 hover:bg-zinc-600" },
] as const

const POS_LABELS: Record<string, string> = {
  ADJ: "Adjective", ADP: "Adposition", ADV: "Adverb", AUX: "Auxiliary",
  CCONJ: "Coord. Conjunction", DET: "Determiner", INTJ: "Interjection",
  NOUN: "Noun", NUM: "Numeral", PART: "Particle", PRON: "Pronoun",
  PROPN: "Proper Noun", PUNCT: "Punctuation", SCONJ: "Subord. Conjunction",
  SYM: "Symbol", VERB: "Verb", X: "Other",
}

const FEAT_VALUE_LABELS: Record<string, string> = {
  Masc: "Masculine", Fem: "Feminine", Neut: "Neuter",
  Sing: "Singular", Plur: "Plural", Dual: "Dual",
  Nom: "Nominative", Gen: "Genitive", Dat: "Dative", Acc: "Accusative",
  Ins: "Instrumental", Loc: "Locative", Voc: "Vocative", Par: "Partitive",
  Past: "Past", Pres: "Present", Fut: "Future",
  Imp: "Imperfective", Perf: "Perfective",
  Anim: "Animate", Inan: "Inanimate",
  Ind: "Indicative", Cnd: "Conditional", Sub: "Subjunctive",
  Act: "Active", Pass: "Passive",
  "1": "1st", "2": "2nd", "3": "3rd",
}

const LABEL_CLASSES: Record<string, string> = {
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
}

const FREQ_TIER_LABELS: Record<string, string> = {
  very_common: "Very common",
  common:      "Common",
  uncommon:    "Uncommon",
  rare:        "Rare",
}

function FrequencyBadge({ freq }: { freq: FrequencyInfo }) {
  const cls = FREQ_TIER_CLASSES[freq.tier] ?? "bg-zinc-700/60 text-zinc-400"
  const label = FREQ_TIER_LABELS[freq.tier] ?? freq.tier
  return (
    <span className={cn("inline-block rounded px-1.5 py-0.5 text-xs", cls)}>
      {label} <span className="opacity-60">#{freq.rank}</span>
    </span>
  )
}

function parseFeats(feats: string): Array<{ key: string; value: string }> {
  if (!feats) return []
  return feats.split("|").flatMap((pair) => {
    const [key, val] = pair.split("=")
    if (key === "Gender") return []  // shown in the gender field
    return [{ key, value: FEAT_VALUE_LABELS[val] ?? val }]
  })
}

interface DefinitionPanelProps {
  token: TokenWithStatus
  language: string
  languageId: number
  languageCode: string
}

export function DefinitionPanel({ token, language, languageId, languageCode }: DefinitionPanelProps) {
  const { clearActive, setActiveToken, setSelectedText, activeToken, selectedText, selectedTokens } = useReaderStore()
  const queryClient = useQueryClient()

  const isSelectionMode = !!selectedText
  const isOverLimit = isSelectionMode && selectedText.length > MAX_SELECTION_CHARS

  const grammarMutation = useMutation<GrammarExplainResponse, Error>({
    mutationFn: () => {
      const tokens = (selectedTokens ?? [])
        .filter((t) => t.pos !== "PUNCT")
        .map((t) => ({ w: t.w, l: t.l, pos: t.pos, feats: t.f ?? "", dep_head: t.dep_head ?? 0, dep_rel: t.dep_rel ?? "" }))
      return explainGrammar(tokens, languageCode)
    },
  })

  useEffect(() => {
    grammarMutation.reset()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedText])

  // Vocabulary key: always surface form
  const surfaceKey = token.w
  // For translation/dictionary: use lemma when available
  const lookupWord = token.l || token.w
  // What to translate: the selection (if any) or the lookup word
  const translationTarget = isSelectionMode ? selectedText : lookupWord

  const { data: availability } = useQuery({
    queryKey: ["translation-available"],
    queryFn: getTranslationAvailable,
    staleTime: Infinity,
  })
  const translationEnabled = availability?.available ?? false

  const statusMutation = useMutation({
    mutationFn: (status: string) =>
      upsertWordStatus({
        word: surfaceKey,
        status,
        language_id: languageId,
        lemma: token.l || "",
        pos: token.pos || "",
        reading: token.r || "",
        gender: token.g || "",
        feats: token.f || "",
      }),
    onSuccess: (_, status) => {
      const newStatus = status as TokenWithStatus["status"]

      if (activeToken) {
        setActiveToken({ ...activeToken, status: newStatus })
      }

      queryClient.invalidateQueries({ queryKey: ["vocabulary"] })

      queryClient.setQueriesData<PageListResponse>(
        { queryKey: ["book-pages"] },
        (old) => {
          if (!old) return old
          return {
            ...old,
            items: old.items.map((p) => ({
              ...p,
              tokens: p.tokens.map((t) =>
                t.w === surfaceKey ? { ...t, status: newStatus } : t
              ),
            })),
          }
        }
      )
    },
  })

  const { data: translationData, isLoading: translationLoading, isError: translationError } = useQuery({
    queryKey: ["translation", translationTarget, language],
    queryFn: () => translate(translationTarget, language),
    enabled: translationEnabled && !isOverLimit && !!translationTarget && !!language,
    staleTime: Infinity,
    retry: false,
  })

  const { data: lookupData, isLoading: defsLoading } = useQuery({
    queryKey: ["dictionary", lookupWord, language],
    queryFn: () => lookup(lookupWord, language.slice(0, 2).toLowerCase(), "en"),
    enabled: !isSelectionMode && !!lookupWord && !!language,
    staleTime: Infinity,
  })

  const posLabel = token.pos ? (POS_LABELS[token.pos] ?? token.pos) : null

  return (
    <aside className="flex h-full w-80 flex-col border-l border-zinc-800 bg-zinc-900">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-zinc-800 p-4">
        {isSelectionMode ? (
          /* Selection mode header */
          <div className="min-w-0 flex-1 pr-2">
            <div className="mb-1.5 flex items-center gap-1.5">
              <button
                onClick={() => setSelectedText(null)}
                className="flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100 transition"
              >
                <ArrowLeft className="h-3 w-3" />
                Word view
              </button>
            </div>
            <p className="text-sm text-zinc-300 leading-relaxed line-clamp-3 break-words">
              {selectedText}
            </p>
            <p className="mt-1 text-xs text-zinc-600">
              {selectedText.length} / {MAX_SELECTION_CHARS} chars
            </p>
          </div>
        ) : (
          /* Word mode header */
          <div className="min-w-0 flex-1 pr-2">
            <p className="text-xl font-semibold text-zinc-100 break-words">{token.w}</p>
            {token.l && token.l !== token.w && (
              <p className="text-sm text-zinc-400">{token.l}</p>
            )}
            {posLabel && (
              <span className="mt-1.5 inline-block rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">
                {posLabel}
              </span>
            )}
          </div>
        )}
        <button
          onClick={clearActive}
          aria-label="Close panel"
          className="mt-1 shrink-0 rounded-md p-1 text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-100"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {isSelectionMode ? (
          /* ── Selection mode body ── */
          <>
            {isOverLimit ? (
              <div className="flex items-start gap-2 rounded-lg bg-amber-900/20 p-3 text-xs text-amber-400">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                <span>
                  Selection too long. Please select fewer than {MAX_SELECTION_CHARS} characters
                  (about 3–4 sentences).
                </span>
              </div>
            ) : (
              <div>
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                  Translation
                </p>
                {translationLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin text-zinc-500" />
                ) : translationError ? (
                  <p className="text-xs text-red-400">Translation unavailable</p>
                ) : translationData && translationData.results.length > 0 ? (
                  <div className="space-y-3">
                    {translationData.results.map((r) => (
                      <div key={r.target_lang}>
                        {translationData.results.length > 1 && (
                          <p className="mb-1 text-xs text-zinc-500">
                            {getLanguageLabel(r.target_lang)}
                          </p>
                        )}
                        <div className="rounded-lg bg-zinc-800 p-3 space-y-1">
                          {r.translated_texts.map((t, i) => (
                            <p key={i} className="text-sm text-zinc-200 leading-relaxed">{t}</p>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : !translationEnabled ? (
                  <p className="text-xs text-zinc-600">
                    No translation provider configured.
                  </p>
                ) : null}
              </div>
            )}

            {/* Grammar explanation */}
            {!isOverLimit && (
              <div>
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                  Grammar
                </p>
                {grammarMutation.isIdle && (
                  <button
                    onClick={() => grammarMutation.mutate()}
                    disabled={!selectedTokens?.length}
                    className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800 transition disabled:opacity-40"
                  >
                    <BrainCircuit className="h-3.5 w-3.5" />
                    Explain grammar
                  </button>
                )}
                {grammarMutation.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin text-zinc-500" />
                )}
                {grammarMutation.isError && (
                  <p className="text-xs text-red-400">
                    {grammarMutation.error.message.includes("proficiency")
                      ? "Set your proficiency level in Settings first."
                      : "Grammar explanation unavailable. Check LLM configuration."}
                  </p>
                )}
                {grammarMutation.data && (
                  <div className="space-y-3">
                    <div className="rounded-lg bg-zinc-800 p-3 space-y-1.5">
                      {grammarMutation.data.token_annotations.map((a, i) => (
                        <div key={i} className="flex gap-2 text-xs">
                          <span className="font-medium text-zinc-200 w-20 shrink-0">{a.w}</span>
                          <span className="text-zinc-400">{a.annotation}</span>
                        </div>
                      ))}
                    </div>
                    <p className="text-sm text-zinc-300 leading-relaxed">
                      {grammarMutation.data.prose_explanation}
                    </p>
                    <button
                      onClick={() => grammarMutation.reset()}
                      className="text-xs text-zinc-600 hover:text-zinc-400 transition"
                    >
                      Clear
                    </button>
                  </div>
                )}
              </div>
            )}

            <p className="text-xs text-zinc-700 italic">
              Click a word or deselect to return to word view.
            </p>
          </>
        ) : (
          /* ── Word mode body ── */
          <>
            {/* NLP metadata */}
            {(token.r || token.g || token.f) && (
              <div className="rounded-lg bg-zinc-800/60 p-3 space-y-2">
                {token.r && (
                  <div className="flex justify-between gap-2">
                    <span className="text-xs text-zinc-500">Reading</span>
                    <span className="text-xs text-zinc-300">{token.r}</span>
                  </div>
                )}
                {token.g && (
                  <div className="flex justify-between gap-2">
                    <span className="text-xs text-zinc-500">Gender</span>
                    <span className="text-xs text-zinc-300 capitalize">{token.g}</span>
                  </div>
                )}
                {parseFeats(token.f).map(({ key, value }) => (
                  <div key={key} className="flex justify-between gap-2">
                    <span className="text-xs text-zinc-500">{key}</span>
                    <span className="text-xs text-zinc-300">{value}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Status buttons */}
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                Status
              </p>
              <div className="flex flex-wrap gap-1.5">
                {STATUSES.map((s) => (
                  <button
                    key={s.value}
                    disabled={statusMutation.isPending}
                    onClick={() => statusMutation.mutate(s.value)}
                    className={cn(
                      "rounded-md px-2.5 py-1 text-xs font-medium text-white transition",
                      s.color,
                      token.status === s.value && "ring-2 ring-white/40",
                    )}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Translation */}
            {translationEnabled && (
              <div>
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                  Translation
                </p>
                {translationLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin text-zinc-500" />
                ) : translationError ? (
                  <p className="text-xs text-red-400">Translation unavailable</p>
                ) : translationData && translationData.results.length > 0 ? (
                  <div className="space-y-2">
                    {translationData.results.map((r) => (
                      <div key={r.target_lang}>
                        {translationData.results.length > 1 && (
                          <p className="mb-0.5 text-xs text-zinc-500">
                            {getLanguageLabel(r.target_lang)}
                          </p>
                        )}
                        <div className="space-y-0.5">
                          {r.translated_texts.map((t, i) => (
                            <p key={i} className="text-sm text-zinc-200">{t}</p>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            )}

            {/* Dictionary */}
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                Dictionary
              </p>
              {defsLoading ? (
                <Loader2 className="h-4 w-4 animate-spin text-zinc-500" />
              ) : lookupData && lookupData.results.length > 0 ? (
                <div className="space-y-4">
                  {lookupData.results.map((providerResult) => (
                    <div key={providerResult.provider_slug}>
                      {lookupData.results.length > 1 && (
                        <p className="mb-1.5 text-xs font-medium text-zinc-600 uppercase capitalize">
                          {providerResult.provider_slug}
                        </p>
                      )}
                      {providerResult.entries.length === 0 ? (
                        <p className="text-xs text-zinc-600">No entries.</p>
                      ) : (
                        <div className="space-y-3">
                          {providerResult.entries.slice(0, 3).map((entry, i) => (
                            <div key={i} className="rounded-lg bg-zinc-800 p-3">
                              <div className="mb-1.5 flex flex-wrap items-center gap-1">
                                <span className="text-xs font-medium text-zinc-400 uppercase">
                                  {POS_LABELS[entry.pos] ?? entry.pos}
                                </span>
                                {entry.labels?.map((label) => (
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
                                {i === 0 && entry.frequency && (
                                  <FrequencyBadge freq={entry.frequency} />
                                )}
                              </div>
                              {entry.glosses.slice(0, 3).map((gloss, j) => (
                                <p key={j} className="text-sm text-zinc-200">
                                  {j + 1}. {gloss}
                                </p>
                              ))}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-zinc-600">No dictionary entries found.</p>
              )}
            </div>
          </>
        )}
      </div>
    </aside>
  )
}
