"use client"

import { create } from "zustand"
import type { SentenceAlignment } from "@/src/lib/api/audio"

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
  setAlignments: (alignments: SentenceAlignment[]) => void
  tick: (currentTimeMs: number) => void
  play: () => void
  pause: () => void
  seekToSentence: (si: number) => SeekTarget | null
  seekTo: (ms: number, audioFile?: string | null) => void
  clearSeekTarget: () => void
}

export const useAudioPlayerStore = create<AudioPlayerState>((set, get) => ({
  isPlaying: false,
  currentTimeMs: 0,
  activeSentenceIndex: null,
  alignments: [],
  currentAudioFile: null,
  seekTarget: null,

  setAlignments: (alignments) => {
    const currentAudioFile = alignments[0]?.audio_file ?? null
    set({ alignments, activeSentenceIndex: null, currentAudioFile })
  },

  tick: (currentTimeMs) => {
    const { alignments } = get()
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
    const { alignments } = get()
    const alignment = alignments.find((a) => a.sentence_index === si)
    if (!alignment) return null
    return { ms: alignment.audio_start_ms, audioFile: alignment.audio_file ?? null }
  },

  seekTo: (ms, audioFile = null) => {
    set({ seekTarget: { ms, audioFile: audioFile ?? null } })
  },

  clearSeekTarget: () => set({ seekTarget: null }),
}))
