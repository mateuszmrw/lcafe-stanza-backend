import { apiClient } from "./client"

export interface StreakResponse {
  current_streak: number
  longest_streak: number
}

export interface CalendarEntry {
  date: string  // "YYYY-MM-DD"
  pages: number
}

export async function recordActivity(languageId: number): Promise<void> {
  return apiClient("/activity/record", {
    method: "POST",
    body: JSON.stringify({ language_id: languageId }),
  })
}

export async function getStreak(languageId: number): Promise<StreakResponse> {
  return apiClient(`/activity/streak?language_id=${languageId}`)
}

export async function getCalendar(languageId: number): Promise<CalendarEntry[]> {
  return apiClient(`/activity/calendar?language_id=${languageId}`)
}
