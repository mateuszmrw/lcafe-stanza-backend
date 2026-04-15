"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"
import { X, Loader2, AlertTriangle, ArrowLeft, BrainCircuit, Volume2, Copy, Check } from "lucide-react"
import type { PageListResponse, TokenWithStatus } from "@/src/lib/api/books"
import { upsertWordStatus } from "@/src/lib/api/vocabulary"
import { translate, getTranslationAvailable } from "@/src/lib/api/translation"
import { lookup, type FrequencyInfo, type WordForm } from "@/src/lib/api/dictionary"
import { explainGrammar, type GrammarExplainResponse } from "@/src/lib/api/grammar"
import { getSynonymNuance, type SynonymNuanceResponse } from "@/src/lib/api/synonyms"
import { createPhrase } from "@/src/lib/api/phrases"
import { useReaderStore } from "@/src/stores/reader"
import { getLanguageLabel } from "@/src/lib/language-flags"
import { cn } from "@/src/lib/cn"
import { STATUSES } from "@/src/lib/status-colors"
import { READER_CONFIG_DEFAULTS, type ReaderConfig } from "@/src/lib/api/languages"

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

// ── Forms table ────────────────────────────────────────────────────────────────

const _CASE_SET = new Set(["nominative","genitive","dative","accusative","instrumental","prepositional","locative","vocative","partitive","ablative","essive","translative","comitative"])
const _CASE_ORDER = ["nominative","genitive","dative","accusative","instrumental","prepositional","locative","vocative","partitive","ablative","essive","translative","comitative"]
const _CASE_SHORT: Record<string,string> = {
  nominative:"Nom", genitive:"Gen", dative:"Dat", accusative:"Acc",
  instrumental:"Ins", prepositional:"Prep", locative:"Loc", vocative:"Voc",
  partitive:"Par", ablative:"Abl", essive:"Ess", translative:"Tra", comitative:"Com",
}
const _NUM_ORDER = ["singular","plural","dual"]
const _NUM_SHORT: Record<string,string> = { singular:"Sg", plural:"Pl", dual:"Du" }
const _PERSON_NORM: Record<string,string> = {
  "first-person":"1st", "1st":"1st", "second-person":"2nd", "2nd":"2nd", "third-person":"3rd", "3rd":"3rd",
}
const _PERSON_ORDER = ["1st","2nd","3rd"]
const _TENSE_ORDER = ["present","past","imperfect","future","conditional","subjunctive","imperative","pluperfect","aorist"]
const _TENSE_LABEL: Record<string,string> = {
  present:"Present", past:"Past", imperfect:"Imperfect", future:"Future",
  conditional:"Conditional", subjunctive:"Subjunctive", imperative:"Imperative",
  pluperfect:"Pluperfect", aorist:"Aorist", indicative:"Indicative",
}
const _MOOD_SET = new Set(["indicative","subjunctive","conditional","imperative"])
const _SPECIAL_SET = new Set(["participle","infinitive","gerund","transgressive","verbal-noun"])
const _SKIP_TAGS = new Set(["multiword-construction","table-tags","error-unrecognized-form","including-rare","rare-form","misspelling","superseded","obsolete-form"])

function _sectionKey(tags: string[]): string {
  const mood = tags.find(t => _MOOD_SET.has(t))
  const tense = tags.find(t => _TENSE_ORDER.includes(t))
  return [mood, tense].filter(Boolean).join("-") || "other"
}

function DeclensionTable({ forms, activeCase }: { forms: WordForm[]; activeCase?: string }) {
  const cases = _CASE_ORDER.filter(c => forms.some(f => f.tags.includes(c)))
  const nums = _NUM_ORDER.filter(n => forms.some(f => f.tags.includes(n)))
  const lookup = new Map<string,string>()
  for (const f of forms) {
    const c = f.tags.find(t => _CASE_SET.has(t))
    const n = f.tags.find(t => _NUM_ORDER.includes(t)) ?? ""
    if (c) lookup.set(`${c}|${n}`, f.form)
  }
  // Map Stanza case abbr (e.g. "Gen") → wiktionary tag (e.g. "genitive")
  const activeCaseTag = activeCase ? activeCase.toLowerCase() === "prep" ? "prepositional" : Object.entries(_CASE_SHORT).find(([,v]) => v === activeCase)?.[0] : undefined

  return (
    <table className="w-full table-fixed text-xs">
      <thead>
        <tr>
          <th className="w-8 pb-1.5" />
          {nums.map(n => (
            <th key={n} className="pb-1.5 text-left text-[10px] font-medium uppercase tracking-wider text-zinc-600">
              {_NUM_SHORT[n]}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {cases.map((c, i) => {
          const isActive = activeCaseTag === c
          return (
            <tr key={c} className={cn(
              "rounded",
              isActive ? "text-zinc-100" : i % 2 === 0 ? "text-zinc-300" : "text-zinc-400",
            )}>
              <td className={cn(
                "py-1 pr-2 text-[10px] font-medium uppercase tracking-wide whitespace-nowrap",
                isActive ? "text-zinc-300" : "text-zinc-600"
              )}>
                {_CASE_SHORT[c]}
              </td>
              {nums.map(n => (
                <td key={n} className="py-1 pr-2 break-words">
                  {lookup.get(`${c}|${n}`) ?? lookup.get(`${c}|`) ?? <span className="text-zinc-700">—</span>}
                </td>
              ))}
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function ConjugationTable({ forms }: { forms: WordForm[] }) {
  const specials = forms.filter(f => f.tags.some(t => _SPECIAL_SET.has(t)))
  const conjugated = forms.filter(f => !f.tags.some(t => _SPECIAL_SET.has(t)))

  const sectionMap = new Map<string,WordForm[]>()
  for (const f of conjugated) {
    const key = _sectionKey(f.tags)
    if (!sectionMap.has(key)) sectionMap.set(key, [])
    sectionMap.get(key)!.push(f)
  }
  const sections = [...sectionMap.entries()].sort(([a],[b]) => {
    const ai = _TENSE_ORDER.findIndex(t => a.includes(t))
    const bi = _TENSE_ORDER.findIndex(t => b.includes(t))
    return (ai<0?99:ai)-(bi<0?99:bi)
  }).slice(0, 3)

  const persons = _PERSON_ORDER.filter(p =>
    conjugated.some(f => f.tags.some(t => _PERSON_NORM[t] === p))
  )
  const nums = _NUM_ORDER.filter(n => conjugated.some(f => f.tags.includes(n)))

  return (
    <div className="space-y-3">
      {specials.length > 0 && (
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {specials.map((f, i) => {
            const label = f.tags.find(t => _SPECIAL_SET.has(t)) ?? ""
            return (
              <span key={i} className="text-xs">
                <span className="text-zinc-500 capitalize">{label} </span>
                <span className="text-zinc-200">{f.form}</span>
              </span>
            )
          })}
        </div>
      )}
      {sections.map(([key, sf]) => {
        const lookup = new Map<string,string>()
        for (const f of sf) {
          const p = _PERSON_ORDER.find(p => f.tags.some(t => _PERSON_NORM[t] === p))
          const n = f.tags.find(t => _NUM_ORDER.includes(t)) ?? ""
          if (p) lookup.set(`${p}|${n}`, f.form)
        }
        const label = key.split("-").map(p => _TENSE_LABEL[p] ?? p).join(" ")
        return (
          <div key={key}>
            <p className="mb-1 text-xs font-medium text-zinc-400 capitalize">{label}</p>
            <table className="w-full text-xs border-collapse">
              {nums.length > 1 && (
                <thead>
                  <tr>
                    <th className="text-left font-normal text-zinc-600 pr-3 pb-0.5 w-8" />
                    {nums.map(n => <th key={n} className="text-center font-medium text-zinc-500 pb-0.5">{_NUM_SHORT[n]}</th>)}
                  </tr>
                </thead>
              )}
              <tbody>
                {persons.map(p => (
                  <tr key={p} className="border-t border-zinc-800/50">
                    <td className="text-zinc-600 pr-3 py-0.5">{p}</td>
                    {nums.map(n => (
                      <td key={n} className={`py-0.5 text-zinc-200 ${nums.length>1?"text-center":""}`}>
                        {lookup.get(`${p}|${n}`) ?? lookup.get(`${p}|`) ?? "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      })}
      {sectionMap.size > 3 && (
        <p className="text-xs text-zinc-600">+{sectionMap.size - 3} more tenses</p>
      )}
    </div>
  )
}

function FormsTable({ forms, activeCase }: { forms: WordForm[]; activeCase?: string }) {
  const cleaned = forms.filter(f =>
    f.form && !f.tags.some(t => _SKIP_TAGS.has(t))
  )
  if (cleaned.length === 0) return null
  const hasCases = cleaned.some(f => f.tags.some(t => _CASE_SET.has(t)))
  const hasPersons = cleaned.some(f => f.tags.some(t => t in _PERSON_NORM))
  const hasTenses = cleaned.some(f => f.tags.some(t => _TENSE_ORDER.includes(t)))
  if (hasCases) return <DeclensionTable forms={cleaned} activeCase={activeCase} />
  if (hasPersons || hasTenses) return <ConjugationTable forms={cleaned} />
  // Simple: deduplicated flat list
  const seen = new Set<string>()
  const unique = cleaned.filter(f => { if(seen.has(f.form)) return false; seen.add(f.form); return true }).slice(0,10)
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-0.5">
      {unique.map((f, i) => <span key={i} className="text-xs text-zinc-300">{f.form}</span>)}
    </div>
  )
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
  // Gender shown in its own field; Case and Mood shown in dedicated blocks below
  const BLOCK_KEYS = new Set(["Gender", "Case", "Mood"])
  return feats.split("|").flatMap((pair) => {
    const [key, val] = pair.split("=")
    if (BLOCK_KEYS.has(key)) return []
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

export function DefinitionPanel({ token, language, languageId, languageCode, bookId, currentPage, register, readerConfig }: DefinitionPanelProps) {
  const cfg: ReaderConfig = readerConfig ?? READER_CONFIG_DEFAULTS
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

  // Vocabulary key: lemma (since migration 0042 the words table is keyed by lemma)
  const lemmaKey = token?.l || token?.w || ""
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

      queryClient.setQueriesData<PageListResponse>(
        { queryKey: ["book-pages"] },
        (old) => {
          if (!old) return old
          return {
            ...old,
            items: old.items.map((p) => ({
              ...p,
              tokens: p.tokens.map((t) =>
                (t.l || t.w) === lemmaKey ? { ...t, status: newStatus } : t
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

  // Hoisted so both the NLP card and the forms table can use it
  const caseAbbr = token ? extractFeat(token.f, "Case") : null

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
            {/* Sentence context — compact quote */}
            {sentenceContext && (
              <div className="flex items-start gap-2">
                <div className="mt-0.5 w-0.5 shrink-0 self-stretch rounded-full bg-zinc-700" />
                <p className="text-xs text-zinc-500 leading-relaxed italic flex-1">{sentenceContext}</p>
                <button
                  onClick={() => copyToClipboard(sentenceContext, "context")}
                  className="shrink-0 rounded p-0.5 text-zinc-700 transition hover:text-zinc-400"
                  aria-label="Copy sentence"
                >
                  {copiedKey === "context" ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                </button>
              </div>
            )}

            {/* NLP metadata */}
            {(token.r || token.g || token.f || token.dep_rel) && (() => {
              const langCode = languageCode.slice(0, 2)
              const caseName = caseAbbr ? (FEAT_VALUE_LABELS[caseAbbr] ?? caseAbbr) : null
              const caseDesc = caseAbbr ? CASE_DESCRIPTIONS[caseAbbr] : null
              const caseQuestion = caseAbbr ? (CASE_QUESTIONS[langCode]?.[caseAbbr]) : null
              const moodAbbr = extractFeat(token.f, "Mood")
              const moodName = moodAbbr ? (FEAT_VALUE_LABELS[moodAbbr] ?? moodAbbr) : null
              const moodDesc = moodAbbr ? MOOD_DESCRIPTIONS[moodAbbr] : null
              const depLabel = token.dep_rel ? DEP_REL_LABELS[token.dep_rel] : null
              const otherFeats = parseFeats(token.f)
              // Collect all rows for the single NLP card, gated by readerConfig
              const nlpRows: Array<{ label: string; value: string; highlight?: string }> = []
              if (cfg.show_case && caseName) {
                nlpRows.push({
                  label: caseName,
                  value: caseDesc ?? "",
                  highlight: cfg.show_case_question ? (caseQuestion ?? undefined) : undefined,
                })
              }
              if (cfg.show_mood && moodName) {
                nlpRows.push({ label: moodName, value: moodDesc ?? "" })
              }
              if (cfg.show_dep_rel && depLabel && token.dep_rel !== "punct") {
                nlpRows.push({ label: "Role in sentence", value: depLabel })
              }
              if (cfg.show_reading && token.r) {
                nlpRows.push({ label: "Reading", value: token.r })
              }
              if (cfg.show_gender && token.g) {
                const gLabel = FEAT_VALUE_LABELS[token.g.charAt(0).toUpperCase() + token.g.slice(1)] ?? token.g
                nlpRows.push({ label: "Gender", value: gLabel })
              }
              if (cfg.show_feats) {
                for (const { key, value } of otherFeats) {
                  nlpRows.push({ label: key, value })
                }
              }

              if (nlpRows.length === 0) return null
              return (
                <div className="rounded-lg bg-zinc-800/60 divide-y divide-zinc-700/50">
                  {nlpRows.map(({ label, value, highlight }, i) => (
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
              )
            })()}

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

            {/* Dictionary — only render when there's content */}
            {(defsLoading || (lookupData && lookupData.results.length > 0)) && (
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
                              {entry.forms && entry.forms.length > 0 && (
                                <div className="mt-2.5 pt-2 border-t border-zinc-700/40">
                                  <FormsTable forms={entry.forms} activeCase={caseAbbr ?? undefined} />
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
            )}
          </>
        ) : null}
      </div>
      </aside>
    </>
  )
}
