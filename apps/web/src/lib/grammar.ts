/** Grammar annotation constants: dep_rel colors, labels, feats parsing. */

export interface SentenceToken {
  w: string
  pos: string
  feats: string
  dep_head: number  // 1-based, 0 = root
  dep_rel: string
}

// ─── Dep_rel → color category ─────────────────────────────────────────────

type DepCategory = "subject" | "verb" | "object" | "modifier" | "prepositional" | "other"

const DEP_CATEGORY: Record<string, DepCategory> = {
  nsubj: "subject", "nsubj:pass": "subject", csubj: "subject", "csubj:pass": "subject",
  root: "verb", cop: "verb", aux: "verb", "aux:pass": "verb",
  obj: "object", iobj: "object", ccomp: "object", xcomp: "object",
  amod: "modifier", advmod: "modifier", nummod: "modifier", appos: "modifier",
  obl: "prepositional", nmod: "prepositional", case: "prepositional", "obl:agent": "prepositional",
  acl: "modifier", "acl:relcl": "modifier", advcl: "modifier",
}

export function getDepCategory(depRel: string): DepCategory {
  return DEP_CATEGORY[depRel] ?? DEP_CATEGORY[depRel.split(":")[0]] ?? "other"
}

export const DEP_COLORS: Record<DepCategory, string> = {
  subject: "text-blue-400",
  verb: "text-emerald-400",
  object: "text-amber-400",
  modifier: "text-violet-400",
  prepositional: "text-rose-400",
  other: "text-zinc-400",
}

export const DEP_BG_COLORS: Record<DepCategory, string> = {
  subject: "bg-blue-500/15",
  verb: "bg-emerald-500/15",
  object: "bg-amber-500/15",
  modifier: "bg-violet-500/15",
  prepositional: "bg-rose-500/15",
  other: "bg-zinc-500/10",
}

export const ARC_STROKE_COLORS: Record<DepCategory, string> = {
  subject: "#60a5fa",
  verb: "#34d399",
  object: "#fbbf24",
  modifier: "#a78bfa",
  prepositional: "#fb7185",
  other: "#71717a",
}

// ─── Dep_rel → friendly labels (localized) ────────────────────────────────

interface DepLabel {
  en: string
  ru?: string
  de?: string
  pl?: string
}

const DEP_LABELS: Record<string, DepLabel> = {
  nsubj: { en: "subject", ru: "подлежащее", de: "Subjekt", pl: "podmiot" },
  "nsubj:pass": { en: "passive subject", ru: "подлежащее (пассив)", de: "Passivsubjekt", pl: "podmiot (strona bierna)" },
  csubj: { en: "clausal subject", ru: "придаточное подлежащее", de: "Satzsubjekt", pl: "podmiot zdaniowy" },
  obj: { en: "direct object", ru: "прямое дополнение", de: "direktes Objekt", pl: "dopełnienie bliższe" },
  iobj: { en: "indirect object", ru: "косвенное дополнение", de: "indirektes Objekt", pl: "dopełnienie dalsze" },
  root: { en: "verb (root)", ru: "сказуемое", de: "Verb (Wurzel)", pl: "orzeczenie" },
  cop: { en: "copula", ru: "связка", de: "Kopula", pl: "łącznik" },
  aux: { en: "auxiliary", ru: "вспомогательный", de: "Hilfsverb", pl: "czasownik posiłkowy" },
  "aux:pass": { en: "passive auxiliary", ru: "вспом. (пассив)", de: "Passivhilfsverb", pl: "cz. posiłkowy (strona bierna)" },
  amod: { en: "adjective", ru: "определение", de: "Adjektiv", pl: "przydawka" },
  advmod: { en: "adverb", ru: "наречие", de: "Adverb", pl: "przysłówek" },
  nummod: { en: "numeral", ru: "числительное", de: "Zahlwort", pl: "liczebnik" },
  obl: { en: "prepositional", ru: "обстоятельство", de: "Präpositional", pl: "okolicznik" },
  nmod: { en: "noun modifier", ru: "определение", de: "Nomenmodifikator", pl: "przydawka" },
  case: { en: "preposition", ru: "предлог", de: "Präposition", pl: "przyimek" },
  det: { en: "determiner", ru: "определитель", de: "Artikel", pl: "określnik" },
  conj: { en: "conjunction", ru: "сочинение", de: "Konjunktion", pl: "spójnik" },
  cc: { en: "coordinator", ru: "союз", de: "Koordinator", pl: "spójnik" },
  mark: { en: "subordinator", ru: "подчин. союз", de: "Subjunktor", pl: "spójnik podrzędny" },
  xcomp: { en: "complement", ru: "дополнение", de: "Komplement", pl: "dopełnienie" },
  ccomp: { en: "clausal complement", ru: "придаточное", de: "Komplementsatz", pl: "dopełnienie zdaniowe" },
  acl: { en: "adjectival clause", ru: "определит. придаточное", de: "Adjektivsatz", pl: "zdanie przydawkowe" },
  "acl:relcl": { en: "relative clause", ru: "относит. придаточное", de: "Relativsatz", pl: "zdanie względne" },
  advcl: { en: "adverbial clause", ru: "обстоят. придаточное", de: "Adverbialsatz", pl: "zdanie okolicznikowe" },
  appos: { en: "apposition", ru: "приложение", de: "Apposition", pl: "dopowiedzenie" },
  flat: { en: "flat (name)", ru: "имя", de: "Name", pl: "nazwa" },
  fixed: { en: "fixed expression", ru: "фразеологизм", de: "feste Wendung", pl: "wyrażenie stałe" },
  parataxis: { en: "parenthetical", ru: "вводное", de: "Parenthese", pl: "wtrącenie" },
  punct: { en: "punctuation" },
}

export function getDepLabel(depRel: string, langCode?: string): string {
  const entry = DEP_LABELS[depRel] ?? DEP_LABELS[depRel.split(":")[0]]
  if (!entry) return depRel
  const localized = langCode ? (entry as unknown as Record<string, string | undefined>)[langCode] : undefined
  return localized ?? entry.en
}

export function getDepLabelTechnical(depRel: string): string {
  return depRel
}

// ─── Feats parsing ────────────────────────────────────────────────────────

const FEAT_LABELS: Record<string, Record<string, string>> = {
  Case: { Nom: "Nominative", Gen: "Genitive", Dat: "Dative", Acc: "Accusative", Ins: "Instrumental", Loc: "Locative", Voc: "Vocative", Par: "Partitive" },
  Gender: { Masc: "Masculine", Fem: "Feminine", Neut: "Neuter", Com: "Common" },
  Number: { Sing: "Singular", Plur: "Plural" },
  Tense: { Pres: "Present", Past: "Past", Fut: "Future", Imp: "Imperfect" },
  Aspect: { Imp: "Imperfective", Perf: "Perfective" },
  Mood: { Ind: "Indicative", Imp: "Imperative", Sub: "Subjunctive", Cnd: "Conditional" },
}

const PRIORITY_FEATS = ["Case", "Gender", "Number", "Tense", "Aspect", "Mood"]

export interface ParsedFeat {
  key: string
  value: string
  label: string
}

export function parseFeats(feats: string): ParsedFeat[] {
  if (!feats) return []
  return feats
    .split("|")
    .map((pair) => {
      const [key, value] = pair.split("=")
      return { key, value, label: FEAT_LABELS[key]?.[value] ?? value }
    })
    .filter((f) => PRIORITY_FEATS.includes(f.key))
}

// ─── Arc diagram max tokens ──────────────────────────────────────────────

export const MAX_ARC_TOKENS = 15
