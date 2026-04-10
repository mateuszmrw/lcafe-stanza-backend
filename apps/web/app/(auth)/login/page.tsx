"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"
import { BookOpen, Loader2 } from "lucide-react"
import { login } from "@/src/lib/api/auth"
import { useAuth } from "@/src/stores/auth"
import { ApiError } from "@/src/lib/api/client"
import { cn } from "@/src/lib/cn"

const schema = z.object({
  email: z.email("Invalid email address"),
  password: z.string().min(1, "Password is required"),
})

type FormData = z.infer<typeof schema>

export default function LoginPage() {
  const router = useRouter()
  const { setTokens } = useAuth()
  const [apiError, setApiError] = useState("")

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  async function onSubmit(data: FormData) {
    setApiError("")
    try {
      const tokens = await login(data.email, data.password)
      setTokens(tokens.access_token, tokens.refresh_token)
      router.replace("/library")
    } catch (err) {
      if (err instanceof ApiError) {
        setApiError(err.message)
      } else {
        setApiError("Something went wrong. Please try again.")
      }
    }
  }

  return (
    <>
      <div className="mb-6 flex flex-col items-center gap-2">
        <BookOpen className="h-8 w-8 text-blue-400" />
        <h1 className="text-xl font-semibold text-zinc-100">Sign in to Slovo</h1>
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
            Password
          </label>
          <input
            {...register("password")}
            type="password"
            autoComplete="current-password"
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
          Sign in
        </button>
      </form>

      <p className="mt-5 text-center text-sm text-zinc-500">
        No account?{" "}
        <Link href="/register" className="text-blue-400 hover:text-blue-300">
          Create one
        </Link>
      </p>
    </>
  )
}
