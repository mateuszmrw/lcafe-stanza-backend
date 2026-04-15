"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ChevronDown, Globe } from "lucide-react"
import { listLanguages } from "@/src/lib/api/languages"
import { updateActiveLanguage, updateProficiency } from "@/src/lib/api/users"
import { useAuth } from "@/src/stores/auth"
import { cn } from "@/src/lib/cn"

const PROFICIENCY_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"] as const

export function LanguageSwitcher() {
  const [open, setOpen] = useState(false)
  const [showProficiencyDialog, setShowProficiencyDialog] = useState(false)
  const [selectedProficiency, setSelectedProficiency] = useState<string | null>(null)
  const { activeLanguage, setActiveLanguage } = useAuth()
  const queryClient = useQueryClient()

  const { data: languages = [] } = useQuery({
    queryKey: ["languages"],
    queryFn: listLanguages,
    staleTime: Infinity,
  })

  const mutation = useMutation({
    mutationFn: (languageId: number) => updateActiveLanguage(languageId),
    onSuccess: (profile) => {
      if (profile.active_language_id && profile.active_language_code && profile.active_language_name) {
        setActiveLanguage({
          id: profile.active_language_id,
          code: profile.active_language_code,
          name: profile.active_language_name,
        })
      }
      queryClient.invalidateQueries({ queryKey: ["books"] })
      setOpen(false)
      if (!profile.proficiency_level) {
        setSelectedProficiency(null)
        setShowProficiencyDialog(true)
      }
    },
  })

  const proficiencyMutation = useMutation({
    mutationFn: (level: string) => updateProficiency({ proficiency_level: level }),
    onSuccess: () => {
      setShowProficiencyDialog(false)
      setSelectedProficiency(null)
      queryClient.invalidateQueries({ queryKey: ["me"] })
    },
  })

  return (
    <>
      <div className="relative px-3">
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center justify-between gap-2 rounded-md px-3 py-2 text-sm transition hover:bg-zinc-800"
        >
          <span className="flex items-center gap-2 text-zinc-300">
            <Globe className="h-4 w-4 text-zinc-500" />
            {activeLanguage ? activeLanguage.name : <span className="text-zinc-500">No language</span>}
          </span>
          <ChevronDown className={cn("h-3.5 w-3.5 text-zinc-500 transition-transform", open && "rotate-180")} />
        </button>

        {open && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
            <div className="absolute left-3 right-3 z-20 mt-1 overflow-hidden rounded-lg border border-zinc-700 bg-zinc-800 py-1 shadow-lg">
              {languages.map((lang) => (
                <button
                  key={lang.id}
                  disabled={mutation.isPending}
                  onClick={() => mutation.mutate(lang.id)}
                  className={cn(
                    "flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition hover:bg-zinc-700",
                    activeLanguage?.id === lang.id
                      ? "text-blue-400"
                      : "text-zinc-300"
                  )}
                >
                  {lang.flag_emoji && <span>{lang.flag_emoji}</span>}
                  {lang.name}
                  {activeLanguage?.id === lang.id && (
                    <span className="ml-auto text-xs text-blue-500">active</span>
                  )}
                </button>
              ))}
              {languages.length === 0 && (
                <p className="px-3 py-2 text-xs text-zinc-500">No languages configured</p>
              )}
            </div>
          </>
        )}
      </div>

      {showProficiencyDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-sm rounded-xl border border-zinc-700 bg-zinc-900 p-6 shadow-xl">
            <h2 className="mb-1 text-base font-semibold text-zinc-100">Set your proficiency</h2>
            <p className="mb-5 text-sm text-zinc-400">
              What&apos;s your level in{" "}
              <span className="font-medium text-zinc-200">{activeLanguage?.name}</span>?
            </p>
            <div className="mb-6 grid grid-cols-3 gap-2">
              {PROFICIENCY_LEVELS.map((level) => (
                <button
                  key={level}
                  onClick={() => setSelectedProficiency(level)}
                  className={cn(
                    "rounded-lg border py-2 text-sm font-medium transition",
                    selectedProficiency === level
                      ? "border-blue-500 bg-blue-500/10 text-blue-400"
                      : "border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200"
                  )}
                >
                  {level}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowProficiencyDialog(false)}
                className="flex-1 rounded-lg border border-zinc-700 py-2 text-sm text-zinc-400 transition hover:border-zinc-500 hover:text-zinc-200"
              >
                Skip
              </button>
              <button
                disabled={!selectedProficiency || proficiencyMutation.isPending}
                onClick={() => selectedProficiency && proficiencyMutation.mutate(selectedProficiency)}
                className="flex-1 rounded-lg bg-blue-600 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {proficiencyMutation.isPending ? "Saving…" : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
