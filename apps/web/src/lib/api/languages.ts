import { apiClient } from "./client"

export interface ReaderConfig {
  show_reading: boolean
  show_case: boolean
  show_case_question: boolean
  show_mood: boolean
  show_dep_rel: boolean
  show_gender: boolean
  show_feats: boolean
}

export const READER_CONFIG_DEFAULTS: ReaderConfig = {
  show_reading: true,
  show_case: true,
  show_case_question: false,
  show_mood: true,
  show_dep_rel: true,
  show_gender: true,
  show_feats: true,
}

export const READER_CONFIG_LABELS: Record<keyof ReaderConfig, string> = {
  show_reading: "Reading (furigana / pinyin)",
  show_case: "Case block",
  show_case_question: "Case mnemonic question",
  show_mood: "Verb mood block",
  show_dep_rel: "Role in sentence",
  show_gender: "Gender",
  show_feats: "Other features (animacy, number, …)",
}

export interface Language {
  id: number
  code: string
  name: string
  flag_emoji: string | null
  reader_config: Partial<ReaderConfig>
}

export function resolveReaderConfig(lang: Pick<Language, "reader_config">): ReaderConfig {
  return { ...READER_CONFIG_DEFAULTS, ...lang.reader_config } as ReaderConfig
}

export async function listLanguages(): Promise<Language[]> {
  return apiClient("/languages")
}
