/**
 * Binary search variants. These are pure functions so they can be unit-tested
 * in isolation and reused anywhere — not just in the audio player store.
 */

/**
 * Upper-bound binary search: returns the index of the first entry whose
 * `key(entry) > target`. Returns `arr.length` if every entry's key is ≤ target.
 *
 * This matches C++ `std::upper_bound` semantics. To find the active entry at
 * time `t` in a sorted timeline, call this with `target = t` and step back one:
 *
 * ```
 * const idx = upperBoundBy(timeline, now, (e) => e.startMs)
 * const active = idx > 0 ? timeline[idx - 1] : null
 * ```
 */
export function upperBoundBy<T>(arr: readonly T[], target: number, key: (item: T) => number): number {
  let left = 0
  let right = arr.length
  while (left < right) {
    const mid = (left + right) >>> 1
    if (key(arr[mid]) <= target) {
      left = mid + 1
    } else {
      right = mid
    }
  }
  return left
}
