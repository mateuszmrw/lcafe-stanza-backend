"use client"

import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, Check } from "lucide-react"
import { getProfile, updateProfile, updateProficiency, toggleCoref, updateExerciseSettings } from "@/src/lib/api/users"
import { useAuth } from "@/src/stores/auth"

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
  const { activeLanguage } = useAuth()
  const [usernameValue, setUsernameValue] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [saved, setSaved] = useState<"username" | "password" | "proficiency" | "exercises" | null>(null)
  const [error, setError] = useState("")
  const [proficiencyLevel, setProficiencyLevel] = useState("")
  const [nativeLanguage, setNativeLanguage] = useState("")
  const [autoIgnorePropn, setAutoIgnorePropn] = useState(true)
  const [corefEnabled, setCorefEnabled] = useState(false)
  const [corefPending, setCorefPending] = useState(false)
  const [corefMessage, setCorefMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null)
  const [exercisesEnabled, setExercisesEnabled] = useState(true)
  const [exerciseInterval, setExerciseInterval] = useState(5)

  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: getProfile,
  })

  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: ["profile"] })
  }, [activeLanguage?.id, queryClient])

  useEffect(() => {
    if (profile) {
      setUsernameValue(profile.username)
      setProficiencyLevel(profile.proficiency_level ?? "")
      setNativeLanguage(profile.native_language_code ?? "")
      setAutoIgnorePropn(profile.auto_ignore_proper_nouns ?? true)
      setCorefEnabled(profile.coref_enabled ?? false)
      setExercisesEnabled(profile.exercises_enabled ?? true)
      setExerciseInterval(profile.exercise_interval_pages ?? 5)
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

  const exercisesMutation = useMutation({
    mutationFn: updateExerciseSettings,
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
        auto_ignore_proper_nouns: autoIgnorePropn,
      })
      setSaved("proficiency")
      setTimeout(() => setSaved(null), 2000)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update learning profile")
    }
  }

  async function handleSaveExercises() {
    setError("")
    setSaved(null)
    try {
      await exercisesMutation.mutateAsync({
        exercises_enabled: exercisesEnabled,
        exercise_interval_pages: exerciseInterval,
      })
      setSaved("exercises")
      setTimeout(() => setSaved(null), 2000)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update exercise settings")
    }
  }

  async function handleCorefToggle(enabled: boolean) {
    if (!profile?.active_language_id) return
    setCorefEnabled(enabled)
    setCorefPending(true)
    setCorefMessage(null)
    try {
      const res = await toggleCoref(profile.active_language_id, enabled)
      setCorefEnabled(res.coref_enabled)
      setCorefMessage(
        res.retokenize_enqueued
          ? { type: "ok", text: "Coreference enabled — re-tokenization enqueued for your library." }
          : { type: "ok", text: res.coref_enabled ? "Coreference enabled." : "Coreference disabled." }
      )
      setTimeout(() => setCorefMessage(null), 4000)
    } catch (e: unknown) {
      setCorefEnabled(!enabled)
      setCorefMessage({ type: "err", text: e instanceof Error ? e.message : "Failed to update setting." })
    } finally {
      setCorefPending(false)
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
        <p className="mb-4 text-xs text-zinc-500">
          {profile?.active_language_name
            ? <>Saved per language — currently editing <span className="text-zinc-300">{profile.active_language_name}</span>. Switch your active language to configure others.</>
            : "Set an active language first to configure your learning profile."}
        </p>
        <fieldset disabled={!profile?.active_language_id} className="space-y-3 disabled:opacity-50">
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
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={autoIgnorePropn}
              onChange={(e) => setAutoIgnorePropn(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-600 bg-zinc-800 accent-blue-500"
            />
            <span className="text-sm text-zinc-300">
              Automatically mark proper nouns as well known
              <span className="ml-1 text-zinc-500">(names, places — counted toward coverage, not surfaced as new words)</span>
            </span>
          </label>
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
        </fieldset>

        {/* Coreference resolution — separate save, may trigger re-tokenization */}
        <div className="mt-4 border-t border-zinc-800 pt-4 space-y-2">
          <label className={`flex items-center gap-3 ${profile?.active_language_id ? "cursor-pointer" : "cursor-not-allowed opacity-50"}`}>
            <input
              type="checkbox"
              checked={corefEnabled}
              disabled={!profile?.active_language_id || corefPending}
              onChange={(e) => handleCorefToggle(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-600 bg-zinc-800 accent-blue-500"
            />
            <span className="text-sm text-zinc-300">
              Enable coreference resolution
              {corefPending && <Loader2 className="ml-2 inline h-3 w-3 animate-spin text-zinc-500" />}
              <span className="ml-1 block text-xs text-zinc-500">
                Links pronouns and noun phrases to the entities they refer to. Enabling triggers a background
                re-tokenization of your library — this may take a few minutes.
              </span>
            </span>
          </label>
          {corefMessage && (
            <p className={`rounded px-3 py-1.5 text-xs ${corefMessage.type === "ok" ? "bg-emerald-900/30 text-emerald-400" : "bg-red-900/30 text-red-400"}`}>
              {corefMessage.text}
            </p>
          )}
        </div>
      </section>

      {/* Exercises */}
      <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <h2 className="mb-1 text-sm font-semibold text-zinc-300 uppercase tracking-wide">Reading Exercises</h2>
        <p className="mb-4 text-xs text-zinc-500">
          Periodic vocabulary drills that appear while reading. Only words you have marked as Learning in the current book are included.
        </p>
        <div className="space-y-4">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={exercisesEnabled}
              onChange={(e) => setExercisesEnabled(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-600 bg-zinc-800 accent-blue-500"
            />
            <span className="text-sm text-zinc-300">Enable reading exercises</span>
          </label>
          <div className={exercisesEnabled ? "" : "pointer-events-none opacity-40"}>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">
              Interval — show exercises every N pages
            </label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min={1}
                max={100}
                value={exerciseInterval}
                onChange={(e) => setExerciseInterval(Math.max(1, Math.min(100, Number(e.target.value))))}
                className="w-24 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-xs text-zinc-500">pages (1 – 100)</span>
            </div>
          </div>
          <button
            onClick={handleSaveExercises}
            disabled={exercisesMutation.isPending}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
          >
            {exercisesMutation.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : saved === "exercises" ? (
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
