"use client"

import { create } from "zustand"

export type FontSize = "sm" | "md" | "lg" | "xl"
export type LineSpacing = "tight" | "normal" | "relaxed"
export type TextWidth = "narrow" | "reading" | "wide" | "full"

interface ReaderSettingsState {
  fontSize: FontSize
  lineSpacing: LineSpacing
  textWidth: TextWidth
  autoMarkRead: boolean
  setFontSize: (v: FontSize) => void
  setLineSpacing: (v: LineSpacing) => void
  setTextWidth: (v: TextWidth) => void
  setAutoMarkRead: (v: boolean) => void
}

const STORAGE_KEY = "slovo-reader-settings"

function load(): Partial<ReaderSettingsState> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}")
  } catch {
    return {}
  }
}

function save(state: Pick<ReaderSettingsState, "fontSize" | "lineSpacing" | "textWidth" | "autoMarkRead">) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {}
}

const saved = typeof window !== "undefined" ? load() : {}

export const useReaderSettings = create<ReaderSettingsState>((set) => ({
  fontSize: (saved.fontSize as FontSize) ?? "md",
  lineSpacing: (saved.lineSpacing as LineSpacing) ?? "normal",
  textWidth: (saved.textWidth as TextWidth) ?? "reading",
  autoMarkRead: (saved.autoMarkRead as boolean) ?? false,

  setFontSize: (fontSize) =>
    set((s) => { save({ ...s, fontSize }); return { fontSize } }),
  setLineSpacing: (lineSpacing) =>
    set((s) => { save({ ...s, lineSpacing }); return { lineSpacing } }),
  setTextWidth: (textWidth) =>
    set((s) => { save({ ...s, textWidth }); return { textWidth } }),
  setAutoMarkRead: (autoMarkRead) =>
    set((s) => { save({ ...s, autoMarkRead }); return { autoMarkRead } }),
}))

export const FONT_SIZE_CLASS: Record<FontSize, string> = {
  sm: "text-base",
  md: "text-lg",
  lg: "text-xl",
  xl: "text-2xl",
}

export const LINE_SPACING_CLASS: Record<LineSpacing, string> = {
  tight: "leading-7",
  normal: "leading-9",
  relaxed: "leading-[3.25rem]",
}

export const TEXT_WIDTH_CLASS: Record<TextWidth, string> = {
  narrow: "max-w-lg",
  reading: "max-w-2xl",
  wide: "max-w-3xl",
  full: "max-w-none",
}
