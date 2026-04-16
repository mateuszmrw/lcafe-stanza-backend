"use client"

import { create } from "zustand"
import type { SentenceAlignment } from "@/src/lib/api/audio"
import type { TimeIndexEntry } from "@/src/lib/api/audio"
import { upperBoundBy } from "@/src/lib/search"

interface SeekTarget {
  ms: number
  audioFile: string | null
}

interface AudioPlayerState {
  isPlaying: boolean
  currentTimeMs: number
  activeSentenceIndex: number | null
  alignments: SentenceAlignment[]
  currentAudioFile: string | null
  seekTarget: SeekTarget | null

  // Time index (YouTube / full-book sync)
  timeIndex: TimeIndexEntry[]
  lastPageNumber: number | null
  pendingPage: number | null  // debounce: page must be stable for 2 ticks
  onPageChange: ((page: number) => void) | null

  setAlignments: (alignments: SentenceAlignment[]) => void
  tick: (currentTimeMs: number) => void
  play: () => void
  pause: () => void
  seekToSentence: (si: number) => SeekTarget | null
  seekTo: (ms: number, audioFile?: string | null) => void
  clearSeekTarget: () => void

  setTimeIndex: (index: TimeIndexEntry[]) => void
  setOnPageChange: (cb: ((page: number) => void) | null) => void
  clearTimeIndex: () => void
  /** Wipe all audio state — used when switching books in the reader. */
  reset: () => void
}

export const useAudioPlayerStore = create<AudioPlayerState>((set, get) => ({
  isPlaying: false,
  currentTimeMs: 0,
  activeSentenceIndex: null,
  alignments: [],
  currentAudioFile: null,
  seekTarget: null,

  timeIndex: [],
  lastPageNumber: null,
  pendingPage: null,
  onPageChange: null,

  setAlignments: (alignments) => {
    const currentAudioFile = alignments[0]?.audio_file ?? null
    set({ alignments, activeSentenceIndex: null, currentAudioFile })
  },

  tick: (currentTimeMs) => {
    const { timeIndex, lastPageNumber, pendingPage, onPageChange, alignments } = get()

    // Time-index mode (YouTube): binary search across all pages
    if (timeIndex.length > 0) {
      const idx = upperBoundBy(timeIndex, currentTimeMs, (e) => e.start_ms)

      if (idx === 0) {
        set({ currentTimeMs, activeSentenceIndex: null, pendingPage: null })
        return
      }

      const entry = timeIndex[idx - 1]
      const isActive = currentTimeMs < entry.end_ms

      if (!isActive) {
        set({ currentTimeMs, activeSentenceIndex: null })
        return
      }

      // Debounce page changes: only fire after 2 consecutive ticks on same page
      if (entry.page_number !== lastPageNumber) {
        if (pendingPage === entry.page_number) {
          // Second tick on this page — commit the change
          set({
            currentTimeMs,
            activeSentenceIndex: entry.sentence_index,
            lastPageNumber: entry.page_number,
            pendingPage: null,
          })
          if (onPageChange) onPageChange(entry.page_number)
        } else {
          // First tick on new page — mark as pending, don't navigate yet
          set({
            currentTimeMs,
            activeSentenceIndex: entry.sentence_index,
            pendingPage: entry.page_number,
          })
        }
      } else {
        set({
          currentTimeMs,
          activeSentenceIndex: entry.sentence_index,
          pendingPage: null,
        })
      }
      return
    }

    // Fallback: per-page linear scan (SMIL/EPUB audio)
    if (!alignments.length) {
      set({ currentTimeMs, activeSentenceIndex: null })
      return
    }

    let active: number | null = null
    for (const a of alignments) {
      if (currentTimeMs >= a.audio_start_ms && currentTimeMs < a.audio_end_ms) {
        active = a.sentence_index
        break
      }
    }

    set({ currentTimeMs, activeSentenceIndex: active })
  },

  play: () => set({ isPlaying: true }),
  pause: () => set({ isPlaying: false }),

  seekToSentence: (si) => {
    const { timeIndex, alignments, lastPageNumber } = get()

    // Try time-index first (YouTube)
    if (timeIndex.length > 0) {
      const entry = timeIndex.find(
        (e) => e.page_number === lastPageNumber && e.sentence_index === si
      )
      if (entry) {
        return { ms: entry.start_ms, audioFile: null }
      }
    }

    // Fallback: per-page alignments
    const alignment = alignments.find((a) => a.sentence_index === si)
    if (!alignment) return null
    return { ms: alignment.audio_start_ms, audioFile: alignment.audio_file ?? null }
  },

  seekTo: (ms, audioFile = null) => {
    set({ seekTarget: { ms, audioFile: audioFile ?? null } })
  },

  clearSeekTarget: () => set({ seekTarget: null }),

  setTimeIndex: (index) => {
    set({ timeIndex: index, lastPageNumber: null, pendingPage: null, activeSentenceIndex: null })
  },

  setOnPageChange: (cb) => {
    set({ onPageChange: cb })
  },

  clearTimeIndex: () => {
    set({ timeIndex: [], lastPageNumber: null, pendingPage: null, onPageChange: null })
  },

  reset: () => {
    set({
      isPlaying: false,
      currentTimeMs: 0,
      activeSentenceIndex: null,
      alignments: [],
      currentAudioFile: null,
      seekTarget: null,
      timeIndex: [],
      lastPageNumber: null,
      pendingPage: null,
      onPageChange: null,
    })
  },
}))
