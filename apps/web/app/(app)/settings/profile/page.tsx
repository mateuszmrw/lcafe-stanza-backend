"use client"

import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, Check } from "lucide-react"
import { getProfile, updateProfile, updateProficiency } from "@/src/lib/api/users"

const PROFICIENCY_LEVELS = [
  { value: "A1", label: "A1 — Beginner" },
  { value: "A2", label: "A2 — Elementary" },
  { value: "B1", label: "B1 — Intermediate" },
  { value: "B2", label: "B2 — Upper Intermediate" },
  { value: "C1", label: "C1 — Advanced" },
  { value: "C2", label: "C2 — Proficient" },
]

const NATIVE_LANGUAGES = [
  { code: "en", label: "English" },
  { code: "pl", label: "Polish" },
  { code: "ru", label: "Russian" },
  { code: "de", label: "German" },
  { code: "fr", label: "French" },
  { code: "es", label: "Spanish" },
  { code: "it", label: "Italian" },
  { code: "pt", label: "Portuguese" },
  { code: "zh", label: "Chinese" },
  { code: "ja", label: "Japanese" },
  { code: "ko", label: "Korean" },
  { code: "ar", label: "Arabic" },
  { code: "uk", label: "Ukrainian" },
  { code: "cs", label: "Czech" },
  { code: "sk", label: "Slovak" },
  { code: "nl", label: "Dutch" },
  { code: "sv", label: "Swedish" },
  { code: "tr", label: "Turkish" },
]

export default function ProfilePage() {
  const queryClient = useQueryClient()
  const [usernameValue, setUsernameValue] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [saved, setSaved] = useState<"username" | "password" | "proficiency" | null>(null)
  const [error, setError] = useState("")
  const [proficiencyLevel, setProficiencyLevel] = useState("")
  const [nativeLanguage, setNativeLanguage] = useState("")

  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: getProfile,
  })

  useEffect(() => {
    if (profile) {
      setUsernameValue(profile.username)
      setProficiencyLevel(profile.proficiency_level ?? "")
      setNativeLanguage(profile.native_language_code ?? "")
    }
  }, [profile])

  const mutation = useMutation({
    mutationFn: updateProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] })
    },
  })

  const proficiencyMutation = useMutation({
    mutationFn: updateProficiency,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] })
    },
  })

  async function handleSaveUsername() {
    setError("")
    setSaved(null)
    try {
      await mutation.mutateAsync({ username: usernameValue })
      setSaved("username")
      setTimeout(() => setSaved(null), 2000)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update username")
    }
  }

  async function handleSaveProficiency() {
    setError("")
    setSaved(null)
    try {
      await proficiencyMutation.mutateAsync({
        proficiency_level: proficiencyLevel || undefined,
        native_language_code: nativeLanguage || undefined,
      })
      setSaved("proficiency")
      setTimeout(() => setSaved(null), 2000)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update learning profile")
    }
  }

  async function handleSavePassword() {
    setError("")
    setSaved(null)
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match")
      return
    }
    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters")
      return
    }
    try {
      await mutation.mutateAsync({ password: newPassword })
      setSaved("password")
      setNewPassword("")
      setConfirmPassword("")
      setTimeout(() => setSaved(null), 2000)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update password")
    }
  }

  if (isLoading) {
    return <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
  }

  return (
    <div className="space-y-6">
      {/* Account info */}
      <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <h2 className="mb-4 text-sm font-semibold text-zinc-300 uppercase tracking-wide">Account</h2>
        <dl className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <dt className="text-zinc-500">Email</dt>
            <dd className="text-zinc-200">{profile?.email}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-zinc-500">Role</dt>
            <dd className="text-zinc-200 capitalize">{profile?.role}</dd>
          </div>
        </dl>
      </section>

      {/* Username */}
      <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <h2 className="mb-4 text-sm font-semibold text-zinc-300 uppercase tracking-wide">Username</h2>
        <div className="flex gap-2">
          <input
            value={usernameValue}
            onChange={(e) => setUsernameValue(e.target.value)}
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSaveUsername}
            disabled={mutation.isPending || !usernameValue || usernameValue === profile?.username}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
          >
            {mutation.isPending && saved === null ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : saved === "username" ? (
              <Check className="h-3.5 w-3.5" />
            ) : null}
            Save
          </button>
        </div>
      </section>

      {/* Learning profile */}
      <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <h2 className="mb-1 text-sm font-semibold text-zinc-300 uppercase tracking-wide">Learning Profile</h2>
        <p className="mb-4 text-xs text-zinc-500">Used for grammar explanations — sets the level and language of detail.</p>
        <div className="space-y-3">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Proficiency level</label>
            <select
              value={proficiencyLevel}
              onChange={(e) => setProficiencyLevel(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">— not set —</option>
              {PROFICIENCY_LEVELS.map((l) => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Native language</label>
            <select
              value={nativeLanguage}
              onChange={(e) => setNativeLanguage(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">— not set —</option>
              {NATIVE_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          </div>
          <button
            onClick={handleSaveProficiency}
            disabled={proficiencyMutation.isPending}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
          >
            {proficiencyMutation.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : saved === "proficiency" ? (
              <Check className="h-3.5 w-3.5" />
            ) : null}
            Save
          </button>
        </div>
      </section>

      {/* Password */}
      <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <h2 className="mb-4 text-sm font-semibold text-zinc-300 uppercase tracking-wide">Change Password</h2>
        <div className="space-y-3">
          <input
            type="password"
            placeholder="New password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="password"
            placeholder="Confirm new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSavePassword}
            disabled={mutation.isPending || !newPassword || !confirmPassword}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
          >
            {mutation.isPending && saved === null ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : saved === "password" ? (
              <Check className="h-3.5 w-3.5" />
            ) : null}
            Update Password
          </button>
        </div>
      </section>

      {error && (
        <p className="rounded-lg bg-red-900/30 px-3 py-2 text-sm text-red-400">{error}</p>
      )}
    </div>
  )
}
