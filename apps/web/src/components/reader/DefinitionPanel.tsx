"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"
import { X, Loader2, AlertTriangle, ArrowLeft, BrainCircuit, Volume2, Copy, Check } from "lucide-react"
import type { PageListResponse, TokenWithStatus } from "@/src/lib/api/books"
import { AnnotatedSentence } from "./AnnotatedSentence"
import { upsertWordStatus } from "@/src/lib/api/vocabulary"
import { translate, getTranslationAvailable } from "@/src/lib/api/translation"
import { lookup } from "@/src/lib/api/dictionary"
import { explainGrammar, type GrammarExplainResponse } from "@/src/lib/api/grammar"
import { getSynonymNuance, type SynonymNuanceResponse } from "@/src/lib/api/synonyms"
import { createPhrase } from "@/src/lib/api/phrases"
import { useReaderStore } from "@/src/stores/reader"
import { getLanguageLabel } from "@/src/lib/language-flags"
import { cn } from "@/src/lib/cn"
import { STATUSES } from "@/src/lib/status-colors"
import { getLemmaKey } from "@/src/lib/tokens"
import { READER_CONFIG_DEFAULTS, type ReaderConfig } from "@/src/lib/api/languages"
import {
  CcCedictEntryCard,
  DictCcEntryCard,
  FrequencyBadge,
  KrdictEntryCard,
  LABEL_CLASSES,
  OpenRussianEntryCard,
  POS_LABELS,
} from "./dictionary/DictionaryEntryCards"
import { FormsTable } from "./dictionary/FormsTable"
import { MorphemePopover } from "./MorphemePopover"
import { getMorphemeRole } from "@/src/lib/morpheme-classifier"
import { getMorphemeColorClass } from "@/src/lib/morpheme-colors"

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



const FEAT_VALUE_LABELS: Record<string, string> = {
  Masc: "Masculine", Fem: "Feminine", Neut: "Neuter",
  Sing: "Singular", Plur: "Plural", Dual: "Dual",
  Nom: "Nominative", Gen: "Genitive", Dat: "Dative", Acc: "Accusative",
  Ins: "Instrumental", Loc: "Locative", Voc: "Vocative", Par: "Partitive",
  Abl: "Ablative", Ess: "Essive", Tra: "Translative", Com: "Comitative",
  Past: "Past", Pres: "Present", Fut: "Future",
  Imp: "Imperfective", Perf: "Perfective",
  Anim: "Animate", Inan: "Inanimate",
  Ind: "Indicative", Cnd: "Conditional", Sub: "Subjunctive",
  Act: "Active", Pass: "Passive",
  "1": "1st", "2": "2nd", "3": "3rd",
}

// Brief description of what each case is used for (language-neutral)
const CASE_DESCRIPTIONS: Record<string, string> = {
  Nom: "Subject of the sentence",
  Gen: "Possession, absence, or quantity",
  Dat: "Indirect object — recipient",
  Acc: "Direct object",
  Ins: "Instrument, accompaniment, or means",
  Loc: "Location — used with prepositions",
  Voc: "Direct address",
  Par: "Partitive — portion of a whole",
  Abl: "Separation, means, or accompaniment",
  Ess: "State or condition",
  Tra: "Change of state or result",
}

// "What question does this case answer?" — a standard grammar-school mnemonic.
// Keyed by 2-letter language code, then Stanza case abbreviation.
const CASE_QUESTIONS: Record<string, Partial<Record<string, string>>> = {
  ru: {
    Nom: "Кто? Что?",
    Gen: "Кого? Чего?",
    Dat: "Кому? Чему?",
    Acc: "Кого? Что?",
    Ins: "Кем? Чем?",
    Loc: "О ком? О чём?",
    Voc: "—",
    Par: "Чего?",
  },
  pl: {
    Nom: "Kto? Co?",
    Gen: "Kogo? Czego?",
    Dat: "Komu? Czemu?",
    Acc: "Kogo? Co?",
    Ins: "Kim? Czym?",
    Loc: "O kim? O czym?",
    Voc: "—",
  },
  uk: {
    Nom: "Хто? Що?",
    Gen: "Кого? Чого?",
    Dat: "Кому? Чому?",
    Acc: "Кого? Що?",
    Ins: "Ким? Чим?",
    Loc: "На кому? На чому?",
    Voc: "—",
  },
  cs: {
    Nom: "Kdo? Co?",
    Gen: "Koho? Čeho?",
    Dat: "Komu? Čemu?",
    Acc: "Koho? Co?",
    Ins: "Kým? Čím?",
    Loc: "O kom? O čem?",
    Voc: "—",
  },
  sk: {
    Nom: "Kto? Čo?",
    Gen: "Koho? Čoho?",
    Dat: "Komu? Čomu?",
    Acc: "Koho? Čo?",
    Ins: "Kým? Čím?",
    Loc: "O kom? O čom?",
    Voc: "—",
  },
  sr: { Nom: "Ko? Šta?", Gen: "Koga? Čega?", Dat: "Kome? Čemu?", Acc: "Koga? Šta?", Ins: "Kim? Čim?", Loc: "O kome?" },
  hr: { Nom: "Tko? Što?", Gen: "Koga? Čega?", Dat: "Komu? Čemu?", Acc: "Koga? Što?", Ins: "Kime? Čime?", Loc: "O kome?" },
  de: { Nom: "Wer? Was?", Gen: "Wessen?", Dat: "Wem?", Acc: "Wen? Was?" },
  la: { Nom: "Quis? Quid?", Gen: "Cuius?", Dat: "Cui?", Acc: "Quem? Quid?", Abl: "A quo?", Voc: "O!", Loc: "Ubi?" },
  fi: { Nom: "Kuka? Mikä?", Gen: "Kenen? Minkä?", Acc: "Kenet? Minkä?", Dat: "Kenelle? Mille?", Abl: "Keneltä? Miltä?", Ess: "Kenä? Minä?", Tra: "Keneksi? Miksi?" },
  et: { Nom: "Kes? Mis?", Gen: "Kelle? Mille?", Par: "Keda? Mida?" },
  // Korean: particles mark grammatical role — these are the question words taught alongside them
  ko: { Nom: "누가? 무엇이?", Gen: "누구의?", Dat: "누구에게?", Acc: "누구를? 무엇을?", Loc: "어디에?", Ins: "무엇으로?" },
}

// Verb mood descriptions — what the mood signals to the learner
const MOOD_DESCRIPTIONS: Record<string, string> = {
  Ind: "Statement of fact or reality",
  Sub: "Doubt, emotion, necessity, or subjectivity — triggered by certain verbs/conjunctions",
  Cnd: "Hypothetical or polite — 'would' / 'could'",
  Imp: "Command or request",
  Pot: "Possibility — 'can' / 'might'",
  Des: "Desire or wish",
  Jus: "Obligation or exhortation",
}

// Human-readable labels for Universal Dependencies dependency relations.
// Especially useful for Chinese/Japanese where morphology is minimal.
const DEP_REL_LABELS: Record<string, string> = {
  nsubj: "Subject",
  obj: "Object",
  iobj: "Indirect object",
  csubj: "Clausal subject",
  ccomp: "Clausal complement",
  xcomp: "Open clausal complement",
  obl: "Oblique nominal",
  vocative: "Vocative",
  dislocated: "Dislocated",
  advcl: "Adverbial clause",
  advmod: "Adverbial modifier",
  discourse: "Discourse element",
  aux: "Auxiliary",
  cop: "Copula",
  mark: "Marker",
  nmod: "Noun modifier",
  appos: "Apposition",
  nummod: "Numeric modifier",
  amod: "Adjectival modifier",
  det: "Determiner",
  clf: "Classifier (measure word)",
  case: "Case marker / particle",
  conj: "Conjunction",
  cc: "Coordinating conjunction",
  fixed: "Fixed expression",
  flat: "Flat structure (name, etc.)",
  compound: "Compound",
  list: "List",
  parataxis: "Parataxis",
  root: "Root (main verb)",
  dep: "Dependency (unspecified)",
  punct: "Punctuation",
}


// ── End forms table ─────────────────────────────────────────────────────────────

function extractFeat(feats: string, featName: string): string | null {
  if (!feats) return null
  for (const pair of feats.split("|")) {
    const [key, val] = pair.split("=")
    if (key === featName) return val ?? null
  }
  return null
}

function parseFeats(feats: string): Array<{ key: string; value: string }> {
  if (!feats) return []
  // Gender, Case, Mood shown in dedicated blocks; only show these remaining useful feats
  const BLOCK_KEYS = new Set(["Gender", "Case", "Mood"])
  const SHOW_KEYS = new Set(["Number", "Tense", "Aspect", "Voice"])
  return feats.split("|").flatMap((pair) => {
    const [key, val] = pair.split("=")
    if (BLOCK_KEYS.has(key) || !SHOW_KEYS.has(key)) return []
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
  readerConfig?: ReaderConfig
}

const NER_TYPE_LABELS: Record<string, string> = {
  PER: "Person", LOC: "Location", ORG: "Organization", GPE: "Geo-political entity",
  DATE: "Date expression", TIME: "Time expression", NORP: "Nationality / group",
  CARDINAL: "Cardinal number", ORDINAL: "Ordinal number", MONEY: "Monetary value",
  PERCENT: "Percentage", FAC: "Facility", PRODUCT: "Product", EVENT: "Named event",
  WORK_OF_ART: "Work of art", LAW: "Legal document", LANGUAGE: "Language name",
  QUANTITY: "Measurement", MISC: "Named entity",
}

export function DefinitionPanel({ token, language, languageId, languageCode, bookId, currentPage, register, readerConfig }: DefinitionPanelProps) {
  const cfg: ReaderConfig = readerConfig ?? READER_CONFIG_DEFAULTS
  const { clearActive, setActiveToken, setSelectedText, activeToken, selectedText, selectedTokens, panelAnchor, sentenceContext } = useReaderStore()
  const queryClient = useQueryClient()

  // Tab state for word mode (LingQ-style)
  type WordTab = "info" | "grammar" | "dictionary"
  const [wordTab, setWordTab] = useState<WordTab>("info")

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
      queryClient.invalidateQueries({ queryKey: ["phrases", languageId] })
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

  // Vocabulary key: lemma (since migration 0042 the words table is keyed by lemma)
  const lemmaKey = token ? getLemmaKey(token) : ""
  // For translation/dictionary: use lemma when available (not lowercased so
  // the user sees the natural dictionary form)
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
        word: lemmaKey,
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
      queryClient.invalidateQueries({ queryKey: ["books"] })

      const patchPages = (old: PageListResponse | undefined) => {
        if (!old) return old
        return {
          ...old,
          items: old.items.map((p) => ({
            ...p,
            tokens: p.tokens.map((t) =>
              getLemmaKey(t) === lemmaKey ? { ...t, status: newStatus } : t
            ),
          })),
        }
      }
      queryClient.setQueriesData<PageListResponse>({ queryKey: ["book-pages"] }, patchPages)
      queryClient.setQueriesData<PageListResponse>({ queryKey: ["book-all-pages"] }, patchPages)
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
   * Position the floating card near the tapped word.
   * Phone: centered floating popup below/above the word.
   * Tablet: same floating behavior.
   * Desktop (lg+): handled by CSS (inline side panel).
   */
  const anchorStyle = useMemo((): React.CSSProperties => {
    if (!panelAnchor || typeof window === "undefined") return {}
    const w = window.innerWidth
    const isDesktop = w >= 1024

    const PANEL_W = Math.min(w - 24, isDesktop ? 420 : 340)
    const GAP = 8
    const spaceBelow = window.innerHeight - panelAnchor.bottom - GAP
    const maxH = isDesktop
      ? Math.min(window.innerHeight * 0.75, 600)
      : Math.min(window.innerHeight * 0.55, 420)

    const top =
      spaceBelow >= maxH
        ? panelAnchor.bottom + GAP
        : Math.max(GAP, panelAnchor.top - maxH - GAP)

    let left = panelAnchor.x - PANEL_W / 2
    left = Math.max(12, Math.min(left, w - PANEL_W - 12))

    return { top, left, width: PANEL_W, maxHeight: maxH, bottom: "auto" }
  }, [panelAnchor])

  // Hoisted so both the NLP card and the forms table can use it
  const caseAbbr = token ? extractFeat(token.f, "Case") : null

  // Grammar rows — computed once so the tab bar can hide the Grammar tab when empty
  type GrammarRow = { label: string; value: string; highlight?: string }
  const grammarRows = useMemo<GrammarRow[]>(() => {
    if (!token) return []
    if (!(token.r || token.g || token.f || token.dep_rel || token.e)) return []
    const langCode = languageCode.slice(0, 2)
    const caseName = caseAbbr ? (FEAT_VALUE_LABELS[caseAbbr] ?? caseAbbr) : null
    const caseDesc = caseAbbr ? CASE_DESCRIPTIONS[caseAbbr] : null
    const caseQuestion = caseAbbr ? CASE_QUESTIONS[langCode]?.[caseAbbr] : null
    const moodAbbr = extractFeat(token.f, "Mood")
    const moodName = moodAbbr ? (FEAT_VALUE_LABELS[moodAbbr] ?? moodAbbr) : null
    const moodDesc = moodAbbr ? MOOD_DESCRIPTIONS[moodAbbr] : null
    const depLabel = token.dep_rel ? DEP_REL_LABELS[token.dep_rel] : null
    const otherFeats = parseFeats(token.f)
    const rows: GrammarRow[] = []
    if (cfg.show_case && caseName) {
      rows.push({
        label: caseName,
        value: caseDesc ?? "",
        highlight: cfg.show_case_question ? (caseQuestion ?? undefined) : undefined,
      })
    }
    if (cfg.show_mood && moodName) {
      rows.push({ label: moodName, value: moodDesc ?? "" })
    }
    if (cfg.show_dep_rel && depLabel && token.dep_rel !== "punct") {
      rows.push({ label: "Role in sentence", value: depLabel })
    }
    if (cfg.show_reading && token.r) {
      rows.push({ label: "Reading", value: token.r })
    }
    if (cfg.show_gender && token.g) {
      const gLabel =
        FEAT_VALUE_LABELS[token.g.charAt(0).toUpperCase() + token.g.slice(1)] ?? token.g
      rows.push({ label: "Gender", value: gLabel })
    }
    if (cfg.show_feats) {
      for (const { key, value } of otherFeats) {
        rows.push({ label: key, value })
      }
    }
    // xpos: show only when it adds detail beyond upos (non-empty and different)
    if (token.x && token.x !== token.pos) {
      rows.push({ label: "Form class", value: token.x })
    }
    if (token.e) {
      rows.push({ label: "Named entity", value: NER_TYPE_LABELS[token.e] ?? token.e })
    }
    return rows
  }, [token, caseAbbr, cfg, languageCode])

  // Tabs shown for word mode. Grammar is hidden when there's nothing to show.
  const availableTabs = useMemo<WordTab[]>(() => {
    const tabs: WordTab[] = ["info", "dictionary"]
    if (grammarRows.length > 0) tabs.push("grammar")
    return tabs
  }, [grammarRows.length])

  // If the active tab just became unavailable (e.g. switched to a particle), fall back to info.
  useEffect(() => {
    if (!availableTabs.includes(wordTab)) setWordTab("info")
  }, [availableTabs, wordTab])

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-30 bg-black/50"
        onClick={clearActive}
      />

      <aside
        style={anchorStyle}
        className="flex flex-col bg-zinc-900 fixed z-40 rounded-2xl shadow-2xl ring-1 ring-zinc-800 overflow-hidden"
      >

        {/* Header */}
        <div className="flex items-start justify-between border-b border-zinc-800 p-3 md:p-4">
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

      <div className="flex-1 overflow-y-auto p-3 md:p-4 space-y-3 md:space-y-5">
        {isSelectionMode ? (
          /* ── Selection mode body ── */
          <>
            {/* Grammar annotation for selected phrase */}
            {selectedTokens && selectedTokens.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                  Grammar
                </p>
                <AnnotatedSentence
                  tokens={selectedTokens.map((t) => ({
                    w: t.w,
                    pos: t.pos,
                    feats: t.f,
                    dep_head: t.dep_head ?? 0,
                    dep_rel: t.dep_rel ?? "",
                  }))}
                  languageCode={languageCode?.slice(0, 2)}
                />
              </div>
            )}

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
          /* ── Word mode body — tabbed layout ── */
          <>
            {/* Tab bar */}
            <div className="flex rounded-lg bg-zinc-800/60 p-0.5 gap-0.5">
              {availableTabs.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setWordTab(tab)}
                  className={cn(
                    "flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition capitalize",
                    wordTab === tab
                      ? "bg-zinc-700 text-zinc-100 shadow-sm"
                      : "text-zinc-500 hover:text-zinc-300"
                  )}
                >
                  {tab === "info" ? "Info" : tab === "grammar" ? "Grammar" : "Dictionary"}
                </button>
              ))}
            </div>

            {/* ── Tab: Info (status + translation + sentence context) ── */}
            {wordTab === "info" && (
              <>
                {/* Morpheme breakdown — shown only when segmentation is available */}
                {token.m && token.m.length > 1 && (
                  <div className="flex flex-wrap items-center gap-1">
                    {token.m.map((morpheme, i) => {
                      const role = getMorphemeRole(morpheme, languageCode)
                      const colorClass = getMorphemeColorClass(role)
                      return (
                        <MorphemePopover
                          key={i}
                          morpheme={morpheme}
                          languageId={languageId}
                          sourceLang={languageCode.slice(0, 2).toLowerCase()}
                          role={role}
                          colorClass={colorClass}
                        />
                      )
                    })}
                  </div>
                )}

                {/* Sentence context — plain text quote, clamped on mobile */}
                {sentenceContext && (
                  <div className="flex items-start gap-2">
                    <div className="mt-0.5 w-0.5 shrink-0 self-stretch rounded-full bg-zinc-700" />
                    <p className="text-xs text-zinc-500 leading-relaxed italic flex-1 line-clamp-2 md:line-clamp-none">{sentenceContext}</p>
                    <button
                      onClick={() => copyToClipboard(sentenceContext, "context")}
                      className="shrink-0 rounded p-0.5 text-zinc-700 transition hover:text-zinc-400"
                      aria-label="Copy sentence"
                    >
                      {copiedKey === "context" ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                    </button>
                  </div>
                )}

                {/* Status buttons */}
                <div>
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
                        {(() => {
                          const firstTranslation = translationData.results[0]?.translated_texts[0]
                          if (!firstTranslation) return null
                          return (
                            <button
                              onClick={() => {
                                statusMutation.mutate({ status: token.status === "new" ? "learning" : token.status, hint: firstTranslation })
                                setHintSaved(true)
                                setTimeout(() => setHintSaved(false), 2000)
                              }}
                              disabled={statusMutation.isPending}
                              className={cn(
                                "mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg border px-4 py-2.5 text-sm font-medium transition",
                                hintSaved
                                  ? "border-emerald-700 bg-emerald-900/30 text-emerald-400"
                                  : "border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:bg-zinc-800 hover:text-zinc-100"
                              )}
                            >
                              {hintSaved ? "Saved ✓" : "Save words"}
                            </button>
                          )
                        })()}
                      </div>
                    ) : null}
                  </div>
                )}

                {/* Synonyms */}
                <div className="mt-4 pt-3 border-t border-zinc-800">
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
              </>
            )}

            {/* ── Tab: Grammar (NLP metadata) — only rendered when grammarRows is non-empty ── */}
            {wordTab === "grammar" && grammarRows.length > 0 && (
              <div className="rounded-lg bg-zinc-800/60 divide-y divide-zinc-700/50">
                {grammarRows.map(({ label, value, highlight }, i) => (
                  <div key={i} className="flex items-start justify-between gap-3 px-3 py-2">
                    <span className="text-xs text-zinc-500 shrink-0">{label}</span>
                    <div className="text-right min-w-0">
                      {highlight && (
                        <span className="text-xs text-amber-400 font-medium">{highlight}</span>
                      )}
                      {value && (
                        <p className={`text-xs ${highlight ? "text-zinc-500 mt-0.5" : "text-zinc-300"}`}>{value}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* ── Tab: Dictionary ── */}
            {wordTab === "dictionary" && (
              <>
                {(defsLoading || (lookupData && lookupData.results.length > 0)) && (
            <div>
              {defsLoading ? (
                <Loader2 className="h-4 w-4 animate-spin text-zinc-500" />
              ) : lookupData && lookupData.results.length > 0 ? (
                <div className="space-y-4">
                  {lookupData.results.map((providerResult) => (
                    <div key={providerResult.source_dict}>
                      {lookupData.results.length > 1 && (
                        <p className="mb-1.5 text-xs font-medium text-zinc-600 uppercase capitalize">
                          {providerResult.source_dict.replace(/-/g, " ")}
                        </p>
                      )}
                      {providerResult.entries.length === 0 ? (
                        <p className="text-xs text-zinc-600">No entries.</p>
                      ) : (
                        <div className="space-y-3">
                          {providerResult.entries.slice(0, 3).map((entry, i) =>
                            providerResult.source_dict === "openrussian" ? (
                              <OpenRussianEntryCard
                                key={i}
                                entry={entry}
                                index={i}
                                activeCase={caseAbbr ?? undefined}
                              />
                            ) : providerResult.source_dict === "cc-cedict" ? (
                              <CcCedictEntryCard key={i} entry={entry} index={i} />
                            ) : providerResult.source_dict === "dict.cc" ? (
                              <DictCcEntryCard key={i} entry={entry} index={i} />
                            ) : providerResult.source_dict === "krdict" ? (
                              <KrdictEntryCard key={i} entry={entry} index={i} />
                            ) : (
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
                              {entry.forms && entry.forms.length > 0 && (
                                <div className="mt-2.5 pt-2 border-t border-zinc-700/40">
                                  <FormsTable forms={entry.forms} activeCase={caseAbbr ?? undefined} />
                                </div>
                              )}
                            </div>
                            )
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
            )}
              </>
            )}
          </>
        ) : null}
      </div>
      </aside>
    </>
  )
}
