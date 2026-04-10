"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ChevronDown, Globe } from "lucide-react"
import { listLanguages } from "@/src/lib/api/languages"
import { updateActiveLanguage } from "@/src/lib/api/users"
import { useAuth } from "@/src/stores/auth"
import { cn } from "@/src/lib/cn"

export function LanguageSwitcher() {
  const [open, setOpen] = useState(false)
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
    },
  })

  return (
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
  )
}
