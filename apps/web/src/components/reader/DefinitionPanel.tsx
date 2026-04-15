"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"
import { X, Loader2, AlertTriangle, ArrowLeft, BrainCircuit, Volume2, Copy, Check } from "lucide-react"
import type { PageListResponse, TokenWithStatus } from "@/src/lib/api/books"
import { upsertWordStatus } from "@/src/lib/api/vocabulary"
import { translate, getTranslationAvailable } from "@/src/lib/api/translation"
import { lookup, type FrequencyInfo } from "@/src/lib/api/dictionary"
import { explainGrammar, type GrammarExplainResponse } from "@/src/lib/api/grammar"
import { getSynonymNuance, type SynonymNuanceResponse } from "@/src/lib/api/synonyms"
import { createPhrase } from "@/src/lib/api/phrases"
import { useReaderStore } from "@/src/stores/reader"
import { getLanguageLabel } from "@/src/lib/language-flags"
import { cn } from "@/src/lib/cn"

const MAX_SELECTION_CHARS = 500

// Map 2-letter language codes to BCP 47 tags for SpeechSynthesis
const SPEECH_LANG: Record<string, string> = {
  ru: "ru-RU",
  pl: "pl-PL",
  ko: "ko-KR",
  zh: "zh-CN",
  de: "de-DE",
  fr: "fr-FR",
  es: "es-ES",
  ja: "ja-JP",
  it: "it-IT",
  pt: "pt-PT",
}

function speakWord(word: string, langCode: string): void {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return
  window.speechSynthesis.cancel()
  const utt = new SpeechSynthesisUtterance(word)
  utt.lang = SPEECH_LANG[langCode] ?? langCode
  utt.rate = 0.85
  window.speechSynthesis.speak(utt)
}

const STATUSES = [
  { value: "new", label: "New", color: "bg-sky-700 hover:bg-sky-600" },
  { value: "learning", label: "Learning", color: "bg-emerald-600 hover:bg-emerald-500" },
  { value: "known", label: "Known", color: "bg-emerald-900 hover:bg-emerald-800" },
  { value: "well_known", label: "Well known", color: "bg-zinc-700 hover:bg-zinc-600" },
  { value: "ignored", label: "Ignore", color: "bg-zinc-800 hover:bg-zinc-700 text-zinc-400" },
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
  very_rare:   "bg-zinc-800/60 text-zinc-600",
}

const FREQ_TIER_LABELS: Record<string, string> = {
  very_common: "Very common",
  common:      "Common",
  uncommon:    "Uncommon",
  rare:        "Rare",
  very_rare:   "Very rare",
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
  token: TokenWithStatus | null
  language: string
  languageId: number
  languageCode: string
  bookId?: string
  currentPage?: number
  register?: string | null
}

export function DefinitionPanel({ token, language, languageId, languageCode, bookId, currentPage, register }: DefinitionPanelProps) {
  const { clearActive, setActiveToken, setSelectedText, activeToken, selectedText, selectedTokens, panelAnchor, sentenceContext } = useReaderStore()
  const queryClient = useQueryClient()

  // Copy-to-clipboard state
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  function copyToClipboard(text: string, key: string) {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedKey(key)
      setTimeout(() => setCopiedKey(null), 1500)
    })
  }

  const isSelectionMode = !!selectedText
  const isOverLimit = isSelectionMode && selectedText.length > MAX_SELECTION_CHARS

  const synonymsMutation = useMutation<SynonymNuanceResponse, Error>({
    mutationFn: () =>
      getSynonymNuance({
        language_id: languageId,
        language_code: languageCode,
        word: token!.w,
        pos: token!.pos,
        lemma: token!.l || token!.w,
        context_sentence: undefined,
      }),
  })

  const grammarMutation = useMutation<GrammarExplainResponse, Error>({
    mutationFn: () => {
      const tokens = (selectedTokens ?? [])
        .filter((t) => t.pos !== "PUNCT")
        .map((t) => ({ w: t.w, l: t.l, pos: t.pos, feats: t.f ?? "", dep_head: t.dep_head ?? 0, dep_rel: t.dep_rel ?? "" }))
      return explainGrammar(tokens, languageCode, register)
    },
  })

  const [phraseSaved, setPhraseSaved] = useState(false)
  const savePhraseMutation = useMutation({
    mutationFn: () =>
      createPhrase({
        language_id: languageId,
        text: selectedText ?? "",
        translation: translationData?.results[0]?.translated_texts[0] ?? null,
        context: selectedText,
        book_id: bookId ?? null,
        page: currentPage ?? null,
      }),
    onSuccess: () => {
      setPhraseSaved(true)
      setTimeout(() => setPhraseSaved(false), 2000)
    },
  })

  useEffect(() => {
    grammarMutation.reset()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedText])

  useEffect(() => {
    synonymsMutation.reset()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token?.w])

  // Keyboard shortcuts: 1-5 set word status when in word mode
  useEffect(() => {
    if (isSelectionMode || !token) return
    const STATUS_KEYS: Record<string, string> = {
      "1": "new", "2": "learning", "3": "known", "4": "well_known", "5": "ignored",
    }
    function handleKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      const status = STATUS_KEYS[e.key]
      if (status) {
        e.preventDefault()
        statusMutation.mutate({ status })
      }
    }
    document.addEventListener("keydown", handleKey)
    return () => document.removeEventListener("keydown", handleKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSelectionMode, token])

  // Vocabulary key: always surface form (null when in selection-only mode)
  const surfaceKey = token?.w ?? ""
  // For translation/dictionary: use lemma when available
  const lookupWord = token ? (token.l || token.w) : ""
  // What to translate: the selection (if any) or the lookup word
  const translationTarget = isSelectionMode ? selectedText : (lookupWord || null)

  const { data: availability } = useQuery({
    queryKey: ["translation-available"],
    queryFn: getTranslationAvailable,
    staleTime: Infinity,
  })
  const translationEnabled = availability?.available ?? false

  const [hintSaved, setHintSaved] = useState(false)

  const statusMutation = useMutation({
    mutationFn: ({ status, hint }: { status: string; hint?: string | null }) =>
      upsertWordStatus({
        word: surfaceKey,
        status,
        language_id: languageId,
        lemma: token?.l || "",
        pos: token?.pos || "",
        reading: token?.r || "",
        gender: token?.g || "",
        feats: token?.f || "",
        hint,
        sentence_context: sentenceContext ?? undefined,
      }),
    onSuccess: (_, { status }) => {
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
    queryFn: () => translate(translationTarget!, language),
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

  const posLabel = token?.pos ? (POS_LABELS[token.pos] ?? token.pos) : null

  /**
   * On tablet (768–1023px), position the floating card near the tapped word
   * or text selection. Phone and desktop breakpoints are handled by CSS only.
   */
  const anchorStyle = useMemo((): React.CSSProperties => {
    if (!panelAnchor || typeof window === "undefined") return {}
    const w = window.innerWidth
    if (w < 768 || w >= 1024) return {}

    const PANEL_W = 320
    const GAP = 8
    const spaceBelow = window.innerHeight - panelAnchor.bottom - GAP

    const top =
      spaceBelow >= 160
        ? panelAnchor.bottom + GAP
        : Math.max(GAP, panelAnchor.top - Math.min(window.innerHeight * 0.7, 480) - GAP)

    let left = panelAnchor.x - PANEL_W / 2
    left = Math.max(GAP, Math.min(left, w - PANEL_W - GAP))

    return { top, left, bottom: "auto" }
  }, [panelAnchor])

  return (
    <>
      {/* Backdrop — mobile/tablet only */}
      <div
        className="fixed inset-0 z-30 bg-black/50 lg:hidden"
        onClick={clearActive}
      />

      <aside
        style={anchorStyle}
        className={cn(
          // Base: flex column, dark bg, fixed overlay
          "flex flex-col bg-zinc-900 fixed z-40",
          // Phone (<md): full-width bottom drawer
          "inset-x-0 bottom-0 rounded-t-2xl max-h-[75vh]",
          // Tablet (md–lg): floating card — position set by anchorStyle above;
          // CSS only handles visual appearance + resets phone inset
          "md:inset-x-auto md:bottom-auto md:w-80 md:rounded-2xl md:max-h-[70vh] md:shadow-2xl md:ring-1 md:ring-zinc-800",
          // Desktop (lg+): inline side panel — not fixed, full height
          "lg:relative lg:inset-auto lg:z-auto lg:h-full lg:w-80 lg:rounded-none lg:ring-0 lg:border-l lg:border-zinc-800 lg:max-h-none lg:shadow-none"
        )}
      >
        {/* Drag handle — phone only */}
        <div className="flex justify-center pt-3 pb-1 md:hidden">
          <div className="h-1 w-10 rounded-full bg-zinc-700" />
        </div>

        {/* Header */}
        <div className="flex items-start justify-between border-b border-zinc-800 p-4">
        {isSelectionMode ? (
          /* Selection mode header */
          <div className="min-w-0 flex-1 pr-2">
            {activeToken && (
              <div className="mb-1.5 flex items-center gap-1.5">
                <button
                  onClick={() => setSelectedText(null)}
                  className="flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100 transition"
                >
                  <ArrowLeft className="h-3 w-3" />
                  Word view
                </button>
              </div>
            )}
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
            <div className="flex items-center gap-2">
              <p className="text-xl font-semibold text-zinc-100 break-words">{token!.w}</p>
              <button
                onClick={() => speakWord(token!.w, languageCode)}
                aria-label="Pronounce word"
                className="shrink-0 rounded p-1 text-zinc-500 transition hover:bg-zinc-800 hover:text-zinc-200"
              >
                <Volume2 className="h-4 w-4" />
              </button>
              <button
                onClick={() => copyToClipboard(token!.w, "word")}
                aria-label="Copy word"
                className="shrink-0 rounded p-1 text-zinc-500 transition hover:bg-zinc-800 hover:text-zinc-200"
              >
                {copiedKey === "word" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              </button>
            </div>
            {token!.l && token!.l !== token!.w && (
              <p className="text-sm text-zinc-400">{token!.l}</p>
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

            {/* Save phrase */}
            {!isOverLimit && (
              <div>
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                  Phrase
                </p>
                <button
                  onClick={() => savePhraseMutation.mutate()}
                  disabled={savePhraseMutation.isPending || phraseSaved}
                  className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800 transition disabled:opacity-50"
                >
                  {phraseSaved ? "Saved!" : savePhraseMutation.isPending ? "Saving…" : "Save phrase"}
                </button>
              </div>
            )}

            <p className="text-xs text-zinc-700 italic">
              Tap a word to look it up.
            </p>
          </>
        ) : token ? (
          /* ── Word mode body ── */
          <>
            {/* Sentence context */}
            {sentenceContext && (
              <div className="rounded-lg bg-zinc-800/40 p-3">
                <div className="mb-1.5 flex items-center justify-between">
                  <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Context</p>
                  <button
                    onClick={() => copyToClipboard(sentenceContext, "context")}
                    className="rounded p-0.5 text-zinc-600 transition hover:text-zinc-300"
                    aria-label="Copy sentence"
                  >
                    {copiedKey === "context" ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                  </button>
                </div>
                <p className="text-sm text-zinc-300 leading-relaxed">{sentenceContext}</p>
              </div>
            )}

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
                    onClick={() => statusMutation.mutate({ status: s.value })}
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
                            <div key={i} className="flex items-center gap-1.5">
                              <p className="flex-1 text-sm text-zinc-200">{t}</p>
                              <button
                                onClick={() => copyToClipboard(t, `trans-${r.target_lang}-${i}`)}
                                className="shrink-0 rounded p-0.5 text-zinc-600 transition hover:text-zinc-300"
                                aria-label="Copy translation"
                              >
                                {copiedKey === `trans-${r.target_lang}-${i}` ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                    {/* Save first translation as hint + set to Learning */}
                    {(() => {
                      const firstTranslation = translationData.results[0]?.translated_texts[0]
                      if (!firstTranslation) return null
                      return (
                        <button
                          onClick={() => {
                            statusMutation.mutate({ status: "learning", hint: firstTranslation })
                            setHintSaved(true)
                            setTimeout(() => setHintSaved(false), 2000)
                          }}
                          disabled={statusMutation.isPending}
                          className={cn(
                            "mt-1 flex w-full items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition",
                            hintSaved
                              ? "border-emerald-700 bg-emerald-900/30 text-emerald-400"
                              : "border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200"
                          )}
                        >
                          {hintSaved ? "Saved as hint · Learning" : "Save translation + Learning"}
                        </button>
                      )
                    })()}
                  </div>
                ) : null}
              </div>
            )}

            {/* Synonyms */}
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                Synonyms
              </p>
              {synonymsMutation.isIdle && (
                <button
                  onClick={() => synonymsMutation.mutate()}
                  className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800 transition"
                >
                  <BrainCircuit className="h-3.5 w-3.5" />
                  Find synonyms
                </button>
              )}
              {synonymsMutation.isPending && (
                <Loader2 className="h-4 w-4 animate-spin text-zinc-500" />
              )}
              {synonymsMutation.isError && (
                <p className="text-xs text-red-400">
                  {synonymsMutation.error.message.includes("503")
                    ? "No LLM provider configured."
                    : "Synonym lookup failed. Try again."}
                </p>
              )}
              {synonymsMutation.data && synonymsMutation.data.synonyms.length > 0 && (
                <div className="space-y-2">
                  {synonymsMutation.data.synonyms.map((s, i) => (
                    <div key={i} className="rounded-lg bg-zinc-800 p-3 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-zinc-100">{s.word}</span>
                        <span className={cn(
                          "rounded px-1.5 py-0.5 text-xs capitalize",
                          LABEL_CLASSES[s.register.toLowerCase()] ?? "bg-zinc-700/60 text-zinc-400"
                        )}>
                          {s.register}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400 leading-relaxed">{s.nuance}</p>
                      {s.example && (
                        <p className="text-xs text-zinc-500 italic">{s.example}</p>
                      )}
                    </div>
                  ))}
                  <button
                    onClick={() => synonymsMutation.reset()}
                    className="text-xs text-zinc-600 hover:text-zinc-400 transition"
                  >
                    Clear
                  </button>
                </div>
              )}
            </div>

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
        ) : null}
      </div>
      </aside>
    </>
  )
}
