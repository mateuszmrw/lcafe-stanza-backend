"use client"

import { create } from "zustand"
import type { TokenWithStatus } from "@/src/lib/api/books"

interface ReaderState {
  activeToken: (TokenWithStatus & { wordId?: string }) | null
  selectedText: string | null
  selectedTokens: TokenWithStatus[] | null
  setActiveToken: (token: (TokenWithStatus & { wordId?: string }) | null) => void
  // Does NOT clear activeToken — both coexist so word panel switches to selection mode
  setSelectedText: (text: string | null, tokens?: TokenWithStatus[]) => void
  clearActive: () => void
}

export const useReaderStore = create<ReaderState>((set) => ({
  activeToken: null,
  selectedText: null,
  selectedTokens: null,
  setActiveToken: (token) => set({ activeToken: token, selectedText: null, selectedTokens: null }),
  setSelectedText: (text, tokens) => set({ selectedText: text, selectedTokens: tokens ?? null }),
  clearActive: () => set({ activeToken: null, selectedText: null, selectedTokens: null }),
}))
