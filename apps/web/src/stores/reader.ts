"use client"

import { create } from "zustand"
import type { TokenWithStatus } from "@/src/lib/api/books"
import type { CognateData } from "@/src/lib/api/vocabulary"

export interface PanelAnchor {
  /** Horizontal centre of the tapped word or text selection */
  x: number
  /** Top of the bounding rect (for positioning above) */
  top: number
  /** Bottom of the bounding rect (for positioning below) */
  bottom: number
}

interface ReaderState {
  activeToken: (TokenWithStatus & { wordId?: string }) | null
  selectedText: string | null
  selectedTokens: TokenWithStatus[] | null
  /** Position of the last tapped word or committed text selection */
  panelAnchor: PanelAnchor | null
  /** Full sentence text for the currently active token */
  sentenceContext: string | null
  /** Full token array for the active sentence (for grammar annotation) */
  sentenceTokens: TokenWithStatus[] | null
  /** Cognate data for the active token, if any */
  activeCognateData: CognateData | null
  setActiveToken: (token: (TokenWithStatus & { wordId?: string }) | null) => void
  // Does NOT clear activeToken — both coexist so word panel switches to selection mode
  setSelectedText: (text: string | null, tokens?: TokenWithStatus[]) => void
  setPanelAnchor: (anchor: PanelAnchor | null) => void
  setSentenceContext: (context: string | null, tokens?: TokenWithStatus[]) => void
  setActiveCognateData: (data: CognateData | null) => void
  clearActive: () => void
}

export const useReaderStore = create<ReaderState>((set) => ({
  activeToken: null,
  selectedText: null,
  selectedTokens: null,
  panelAnchor: null,
  sentenceContext: null,
  sentenceTokens: null,
  activeCognateData: null,
  setActiveToken: (token) => set({ activeToken: token, selectedText: null, selectedTokens: null }),
  setSelectedText: (text, tokens) => set({ selectedText: text, selectedTokens: tokens ?? null }),
  setPanelAnchor: (anchor) => set({ panelAnchor: anchor }),
  setSentenceContext: (context, tokens) => set({ sentenceContext: context, sentenceTokens: tokens ?? null }),
  setActiveCognateData: (data) => set({ activeCognateData: data }),
  clearActive: () => set({ activeToken: null, selectedText: null, selectedTokens: null, panelAnchor: null, sentenceContext: null, sentenceTokens: null, activeCognateData: null }),
}))
