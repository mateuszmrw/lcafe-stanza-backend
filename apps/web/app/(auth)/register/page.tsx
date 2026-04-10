"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"
import { BookOpen, Loader2 } from "lucide-react"
import { register as registerApi } from "@/src/lib/api/auth"
import { updateProficiency } from "@/src/lib/api/users"
import { useAuth } from "@/src/stores/auth"
import { ApiError } from "@/src/lib/api/client"
import { cn } from "@/src/lib/cn"

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

const schema = z.object({
  email: z.email("Invalid email address"),
  username: z.string().min(3, "Username must be at least 3 characters"),
  password: z.string().min(8, "Password must be at least 8 characters"),
})

type FormData = z.infer<typeof schema>

export default function RegisterPage() {
  const router = useRouter()
  const { setTokens } = useAuth()
  const [apiError, setApiError] = useState("")
  const [proficiencyLevel, setProficiencyLevel] = useState("")
  const [nativeLanguage, setNativeLanguage] = useState("")

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  async function onSubmit(data: FormData) {
    setApiError("")
    try {
      const tokens = await registerApi(data.email, data.username, data.password)
      setTokens(tokens.access_token, tokens.refresh_token)
      if (proficiencyLevel || nativeLanguage) {
        await updateProficiency({
          proficiency_level: proficiencyLevel || undefined,
          native_language_code: nativeLanguage || undefined,
        }).catch(() => {})
      }
      router.replace("/library")
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setApiError("Email already taken. Try logging in instead.")
        } else {
          setApiError(err.message)
        }
      } else {
        setApiError("Something went wrong. Please try again.")
      }
    }
  }

  return (
    <>
      <div className="mb-6 flex flex-col items-center gap-2">
        <BookOpen className="h-8 w-8 text-blue-400" />
        <h1 className="text-xl font-semibold text-zinc-100">Create your account</h1>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-zinc-300">
            Email
          </label>
          <input
            {...register("email")}
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            className={cn(
              "w-full rounded-lg border bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none transition focus:ring-2 focus:ring-blue-500",
              errors.email ? "border-red-500" : "border-zinc-700"
            )}
          />
          {errors.email && (
            <p className="mt-1 text-xs text-red-400">{errors.email.message}</p>
          )}
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-zinc-300">
            Username
          </label>
          <input
            {...register("username")}
            type="text"
            autoComplete="username"
            placeholder="yourname"
            className={cn(
              "w-full rounded-lg border bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none transition focus:ring-2 focus:ring-blue-500",
              errors.username ? "border-red-500" : "border-zinc-700"
            )}
          />
          {errors.username && (
            <p className="mt-1 text-xs text-red-400">{errors.username.message}</p>
          )}
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-zinc-300">
            Password
          </label>
          <input
            {...register("password")}
            type="password"
            autoComplete="new-password"
            placeholder="••••••••"
            className={cn(
              "w-full rounded-lg border bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none transition focus:ring-2 focus:ring-blue-500",
              errors.password ? "border-red-500" : "border-zinc-700"
            )}
          />
          {errors.password && (
            <p className="mt-1 text-xs text-red-400">{errors.password.message}</p>
          )}
        </div>

        <div className="border-t border-zinc-800 pt-4 space-y-3">
          <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
            Learning profile <span className="normal-case text-zinc-600 font-normal">(optional)</span>
          </p>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-300">
              Your level in the target language
            </label>
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
            <label className="mb-1.5 block text-sm font-medium text-zinc-300">
              Your native language
            </label>
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
        </div>

        {apiError && (
          <p className="rounded-lg bg-red-900/30 px-3 py-2 text-sm text-red-400">
            {apiError}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-60"
        >
          {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
          Create account
        </button>
      </form>

      <p className="mt-5 text-center text-sm text-zinc-500">
        Already have an account?{" "}
        <Link href="/login" className="text-blue-400 hover:text-blue-300">
          Sign in
        </Link>
      </p>
    </>
  )
}
