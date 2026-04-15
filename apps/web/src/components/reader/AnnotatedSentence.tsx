"use client"

import {
  type SentenceToken,
  getDepCategory,
  getDepLabel,
  parseFeats,
  DEP_COLORS,
} from "@/src/lib/grammar"

interface AnnotatedSentenceProps {
  tokens: SentenceToken[]
  languageCode?: string
}

export function AnnotatedSentence({ tokens, languageCode }: AnnotatedSentenceProps) {
  const wordTokens = tokens.filter((t) => t.pos !== "PUNCT" && t.w.trim())

  if (!wordTokens.length) return null

  return (
    <div className="rounded-lg border border-zinc-800 overflow-hidden">
      <table className="w-full text-xs">
        <tbody>
          {wordTokens.map((token, i) => {
            const cat = getDepCategory(token.dep_rel)
            const friendly = getDepLabel(token.dep_rel, languageCode)
            const feats = parseFeats(token.feats)
            const caseVal = feats.find((f) => f.key === "Case")

            return (
              <tr key={i} className="border-b border-zinc-800/50 last:border-0">
                {/* Word */}
                <td className={`px-3 py-1.5 font-medium ${DEP_COLORS[cat]}`}>
                  {token.w}
                </td>
                {/* Role */}
                <td className="px-2 py-1.5 text-zinc-500">
                  {friendly}
                </td>
                {/* Case (if present) */}
                <td className="px-2 py-1.5 text-right text-zinc-600">
                  {caseVal?.label ?? ""}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
