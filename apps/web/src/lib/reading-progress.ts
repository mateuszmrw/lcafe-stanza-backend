const STORAGE_KEY = "slovo-reading-progress"

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
