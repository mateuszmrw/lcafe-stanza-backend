import { apiClient } from "./client"

export interface ExerciseCheckResponse {
  should_show: boolean
  candidate_count: number
}

export interface ClozeExercise {
  id: string
  type: "cloze"
  word_id: string
  lemma: string
  sentence_tokens: string[]
  blank_index: number
  correct_form: string
}

export interface MeaningRecallExercise {
  id: string
  type: "meaning_recall"
  word_id: string
  lemma: string
  sentence: string
  highlighted_word: string
  options: string[]
  correct_index: number
}

export interface GrammarMicroDrillExercise {
  id: string
  type: "grammar_micro_drill"
  word_id: string
  lemma: string
  prompt: string
  options: string[]
  correct_index: number
}

export type Exercise = ClozeExercise | MeaningRecallExercise | GrammarMicroDrillExercise

export interface ExerciseSessionResponse {
  session_id: string
  exercises: Exercise[]
}

export interface ExerciseAnswer {
  exercise_id: string
  word_id: string
  answer: string
  exercise_type: string
}

export interface ExerciseCompleteRequest {
  session_id: string
  page: number
  answers: ExerciseAnswer[]
}

export interface ExerciseResult {
  exercise_id: string
  correct: boolean
  correct_form: string
}

export interface WordUpgrade {
  word_id: string
  lemma: string
  old_status: string
  new_status: string
}

export interface ExerciseCompleteResponse {
  results: ExerciseResult[]
  upgrades: WordUpgrade[]
}

export async function checkExercises(bookId: string, page: number): Promise<ExerciseCheckResponse> {
  return apiClient(`/books/${bookId}/exercises/check?page=${page}`)
}

export async function getExercises(
  bookId: string,
  mode: "inline" | "practice" = "inline",
  page?: number,
): Promise<ExerciseSessionResponse> {
  const params = new URLSearchParams({ mode })
  if (page !== undefined) params.set("page", String(page))
  return apiClient(`/books/${bookId}/exercises?${params}`)
}

export async function completeExercises(
  bookId: string,
  data: ExerciseCompleteRequest,
): Promise<ExerciseCompleteResponse> {
  return apiClient(`/books/${bookId}/exercises/complete`, {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function snoozeExercises(
  bookId: string,
  page: number,
): Promise<{ snooze_until_page: number }> {
  return apiClient(`/books/${bookId}/exercises/snooze`, {
    method: "POST",
    body: JSON.stringify({ page }),
  })
}
