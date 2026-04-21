import { RUSSIAN_PREFIXES, RUSSIAN_SUFFIXES } from "./morpheme-roles"

export type MorphemeRole = "prefix" | "root" | "suffix"

export function getMorphemeRole(morpheme: string, languageCode: string): MorphemeRole {
  if (languageCode !== "ru") return "root"
  const m = morpheme.toLowerCase()
  if (RUSSIAN_PREFIXES.has(m)) return "prefix"
  if (RUSSIAN_SUFFIXES.has(m)) return "suffix"
  return "root"
}
