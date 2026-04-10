import type { TokenWithStatus } from "@/src/lib/api/books"

export function groupBySentence(tokens: TokenWithStatus[]): TokenWithStatus[][] {
  const groups: Map<number, TokenWithStatus[]> = new Map()
  for (const token of tokens) {
    const si = token.si ?? 0
    if (!groups.has(si)) groups.set(si, [])
    groups.get(si)!.push(token)
  }
  return Array.from(groups.values())
}

export function sentenceText(tokens: TokenWithStatus[], noWordSpacing: boolean): string {
  const sep = noWordSpacing ? "" : " "
  return tokens
    .filter((t) => t.pos !== "PUNCT" || noWordSpacing)
    .map((t) => t.w)
    .join(sep)
    .trim()
}
