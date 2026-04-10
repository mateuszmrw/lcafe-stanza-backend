"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"

interface User {
  id: string
  email: string
  username: string
  is_admin: boolean
}

interface ActiveLanguage {
  id: number
  code: string
  name: string
}

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  activeLanguage: ActiveLanguage | null
  _hydrated: boolean
  setTokens: (accessToken: string, refreshToken: string) => void
  setUser: (user: User) => void
  setActiveLanguage: (lang: ActiveLanguage | null) => void
  clearTokens: () => void
  _setHydrated: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      activeLanguage: null,
      _hydrated: false,
      setTokens: (accessToken, refreshToken) =>
        set({ accessToken, refreshToken }),
      setUser: (user) => set({ user }),
      setActiveLanguage: (lang) => set({ activeLanguage: lang }),
      clearTokens: () => set({ accessToken: null, refreshToken: null, user: null, activeLanguage: null }),
      _setHydrated: () => set({ _hydrated: true }),
    }),
    {
      name: "slovo-auth",
      onRehydrateStorage: () => (state) => {
        state?._setHydrated()
      },
    }
  )
)

/** Non-React access for use in API client */
export function getAuthStore() {
  return useAuthStore.getState()
}

export function useAuth() {
  const { accessToken, refreshToken, user, activeLanguage, _hydrated, setTokens, setUser, setActiveLanguage, clearTokens } =
    useAuthStore()

  return {
    accessToken,
    refreshToken,
    user,
    activeLanguage,
    isAuthenticated: !!accessToken,
    isHydrated: _hydrated,
    setTokens,
    setUser,
    setActiveLanguage,
    clearTokens,
  }
}
