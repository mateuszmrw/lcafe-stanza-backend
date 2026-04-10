"use client"

import { useEffect, type ReactNode } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/src/stores/auth"
import { AppShell } from "@/src/components/layout/AppShell"
import { getProfile, updateActiveLanguage } from "@/src/lib/api/users"
import { listLanguages } from "@/src/lib/api/languages"

export default function AppLayout({ children }: { children: ReactNode }) {
  const { isAuthenticated, isHydrated, setUser, setActiveLanguage } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (isHydrated && !isAuthenticated) {
      router.replace("/login")
    }
  }, [isAuthenticated, isHydrated, router])

  useEffect(() => {
    if (!isAuthenticated) return
    getProfile().then((profile) => {
      setUser({
        id: profile.id,
        email: profile.email,
        username: profile.username,
        is_admin: profile.role === "admin",
      })
      if (profile.active_language_id && profile.active_language_code && profile.active_language_name) {
        setActiveLanguage({
          id: profile.active_language_id,
          code: profile.active_language_code,
          name: profile.active_language_name,
        })
      } else {
        // No active language — default to English or first available
        listLanguages().then((languages) => {
          const lang = languages.find((l) => l.code === "en") ?? languages[0]
          if (!lang) return
          updateActiveLanguage(lang.id).then((updated) => {
            if (updated.active_language_id && updated.active_language_code && updated.active_language_name) {
              setActiveLanguage({
                id: updated.active_language_id,
                code: updated.active_language_code,
                name: updated.active_language_name,
              })
            }
          }).catch(() => {})
        }).catch(() => {})
      }
    }).catch(() => {
      // ignore — user data is best-effort for UI personalization
    })
  }, [isAuthenticated, setUser, setActiveLanguage])

  if (!isHydrated) return null
  if (!isAuthenticated) return null

  return <AppShell>{children}</AppShell>
}
