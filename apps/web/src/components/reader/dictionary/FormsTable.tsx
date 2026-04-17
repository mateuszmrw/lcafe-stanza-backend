"use client"

import type { WordForm } from "@/src/lib/api/dictionary"
import { cn } from "@/src/lib/cn"

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
  const lookupMap = new Map<string,string>()
  for (const f of forms) {
    const c = f.tags.find(t => _CASE_SET.has(t))
    const n = f.tags.find(t => _NUM_ORDER.includes(t)) ?? ""
    if (c) lookupMap.set(`${c}|${n}`, f.form)
  }
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
                  {lookupMap.get(`${c}|${n}`) ?? lookupMap.get(`${c}|`) ?? <span className="text-zinc-700">—</span>}
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
        const lookupMap = new Map<string,string>()
        for (const f of sf) {
          const p = _PERSON_ORDER.find(p => f.tags.some(t => _PERSON_NORM[t] === p))
          const n = f.tags.find(t => _NUM_ORDER.includes(t)) ?? ""
          if (p) lookupMap.set(`${p}|${n}`, f.form)
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
                        {lookupMap.get(`${p}|${n}`) ?? lookupMap.get(`${p}|`) ?? "—"}
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

export function FormsTable({ forms, activeCase }: { forms: WordForm[]; activeCase?: string }) {
  const cleaned = forms.filter(f =>
    f.form && !f.tags.some(t => _SKIP_TAGS.has(t))
  )
  if (cleaned.length === 0) return null
  const hasCases = cleaned.some(f => f.tags.some(t => _CASE_SET.has(t)))
  const hasPersons = cleaned.some(f => f.tags.some(t => t in _PERSON_NORM))
  const hasTenses = cleaned.some(f => f.tags.some(t => _TENSE_ORDER.includes(t)))
  if (hasCases) return <DeclensionTable forms={cleaned} activeCase={activeCase} />
  if (hasPersons || hasTenses) return <ConjugationTable forms={cleaned} />
  const seen = new Set<string>()
  const unique = cleaned.filter(f => { if(seen.has(f.form)) return false; seen.add(f.form); return true }).slice(0,10)
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-0.5">
      {unique.map((f, i) => <span key={i} className="text-xs text-zinc-300">{f.form}</span>)}
    </div>
  )
}
