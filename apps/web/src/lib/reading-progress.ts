const STORAGE_KEY = "slovo-reading-progress"
const AUDIO_STORAGE_KEY = "slovo-audio-progress"

function getAll(): Record<string, number> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}")
  } catch {
    return {}
  }
}

export function getReadingProgress(bookId: string): number | null {
  return getAll()[bookId] ?? null
}

export function saveReadingProgress(bookId: string, page: number): void {
  const all = getAll()
  all[bookId] = page
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all))
}

interface AudioProgress {
  timeMs: number
  audioFile: string | null
}

function getAllAudio(): Record<string, AudioProgress> {
  try {
    return JSON.parse(localStorage.getItem(AUDIO_STORAGE_KEY) ?? "{}")
  } catch {
    return {}
  }
}

export function getAudioProgress(bookId: string): AudioProgress | null {
  return getAllAudio()[bookId] ?? null
}

export function saveAudioProgress(bookId: string, timeMs: number, audioFile: string | null): void {
  const all = getAllAudio()
  all[bookId] = { timeMs, audioFile }
  localStorage.setItem(AUDIO_STORAGE_KEY, JSON.stringify(all))
}
