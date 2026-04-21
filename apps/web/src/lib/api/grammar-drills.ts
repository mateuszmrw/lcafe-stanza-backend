import { apiClient } from "./client"

/** Mirror of Python normalize_answer — lowercase + strip combining diacritics (stress marks). */
export function normalizeAnswer(text: string): string {
  return [...text.toLowerCase().trim().normalize("NFD")]
    .filter((c) => {
      const cp = c.codePointAt(0) ?? 0
      return cp < 0x0300 || cp > 0x036f  // exclude combining diacritical marks block
    })
    .join("")
}

export type DrillQuestionType = "fill_blank" | "multiple_choice" | "case_identification"
export type DrillSessionType = "form_production" | "case_identification" | "preposition_case" | "aspect_pairs"

export interface DrillQuestion {
  id: string
  type: DrillQuestionType
  lemma: string
  display_lemma: string
  prompt: string
  form_type: string
  sentence?: string
  highlighted_word?: string
  options?: string[]
  correct_form: string
  accepted_forms: string[]
}

export interface DrillSessionResponse {
  session_id: string
  available: boolean
  reason?: string
  questions: DrillQuestion[]
  drill_type: DrillSessionType
}

export interface DrillAnswer {
  question_id: string
  answer: string
}

export interface DrillResult {
  question_id: string
  correct: boolean
  user_answer: string
  correct_form: string
  lemma: string
  form_type: string
}

export interface DrillSubmitResponse {
  score: number
  total: number
  results: DrillResult[]
}

export interface AvailableDrill {
  type: DrillSessionType
  name: string
  description: string
  available: boolean
  reason?: string
}

export interface AvailableDrillsResponse {
  drills: AvailableDrill[]
}

export async function getAvailableDrills(): Promise<AvailableDrillsResponse> {
  return apiClient<AvailableDrillsResponse>("/grammar/drills/available")
}

export async function getDrillSession(
  drillType: DrillSessionType = "form_production",
  sessionSize = 15
): Promise<DrillSessionResponse> {
  return apiClient<DrillSessionResponse>(
    `/grammar/drills?drill_type=${drillType}&session_size=${sessionSize}`
  )
}

export async function submitDrillAnswers(
  sessionId: string,
  answers: DrillAnswer[]
): Promise<DrillSubmitResponse> {
  return apiClient<DrillSubmitResponse>("/grammar/drills/submit", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, answers }),
  })
}
