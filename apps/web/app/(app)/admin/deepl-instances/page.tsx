"use client"

import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, Plus, Trash2, ArrowRight } from "lucide-react"
import {
  getDeepLInstances,
  createDeepLInstance,
  toggleDeepLInstance,
  deleteDeepLInstance,
  type DeepLInstanceResponse,
} from "@/src/lib/api/deepl-instances"
import { LANGUAGE_FLAGS, getLanguageLabel } from "@/src/lib/language-flags"
import { cn } from "@/src/lib/cn"

const LANGUAGE_OPTIONS = Object.entries(LANGUAGE_FLAGS).map(([code, info]) => ({
  code,
  label: `${info.flag} ${info.name}`,
}))

function InstanceRow({ instance }: { instance: DeepLInstanceResponse }) {
  const queryClient = useQueryClient()

  const toggleMutation = useMutation({
    mutationFn: (enabled: boolean) => toggleDeepLInstance(instance.id, enabled),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["deepl-instances"] }),
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteDeepLInstance(instance.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["deepl-instances"] }),
  })

  return (
    <div className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900 px-4 py-3">
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-zinc-200">
          {getLanguageLabel(instance.source_lang)}
        </span>
        <ArrowRight className="h-3.5 w-3.5 text-zinc-600" />
        <span className="text-sm font-medium text-zinc-200">
          {getLanguageLabel(instance.target_lang)}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => toggleMutation.mutate(!instance.enabled)}
          disabled={toggleMutation.isPending}
          className={cn(
            "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none disabled:opacity-50",
            instance.enabled ? "bg-blue-600" : "bg-zinc-700"
          )}
          aria-label={instance.enabled ? "Disable" : "Enable"}
        >
          <span
            className={cn(
              "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition-transform",
              instance.enabled ? "translate-x-4" : "translate-x-0"
            )}
          />
        </button>

        <button
          onClick={() => deleteMutation.mutate()}
          disabled={deleteMutation.isPending}
          className="rounded-lg p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-red-400 transition disabled:opacity-50"
          aria-label="Delete instance"
        >
          {deleteMutation.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Trash2 className="h-3.5 w-3.5" />
          )}
        </button>
      </div>
    </div>
  )
}

function AddInstanceForm() {
  const queryClient = useQueryClient()
  const [sourceLang, setSourceLang] = useState("")
  const [targetLang, setTargetLang] = useState("")

  const createMutation = useMutation({
    mutationFn: () => createDeepLInstance({ source_lang: sourceLang, target_lang: targetLang }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["deepl-instances"] })
      setSourceLang("")
      setTargetLang("")
    },
  })

  const isValid = sourceLang && targetLang && sourceLang !== targetLang

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-zinc-500">
        Add translation pair
      </p>
      <div className="flex items-center gap-2">
        <select
          value={sourceLang}
          onChange={(e) => setSourceLang(e.target.value)}
          className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Source language</option>
          {LANGUAGE_OPTIONS.map((opt) => (
            <option key={opt.code} value={opt.code}>{opt.label}</option>
          ))}
        </select>

        <ArrowRight className="h-4 w-4 shrink-0 text-zinc-600" />

        <select
          value={targetLang}
          onChange={(e) => setTargetLang(e.target.value)}
          className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Target language</option>
          {LANGUAGE_OPTIONS.filter((opt) => opt.code !== sourceLang).map((opt) => (
            <option key={opt.code} value={opt.code}>{opt.label}</option>
          ))}
        </select>

        <button
          onClick={() => createMutation.mutate()}
          disabled={!isValid || createMutation.isPending}
          className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition"
        >
          {createMutation.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Plus className="h-3.5 w-3.5" />
          )}
          Add
        </button>
      </div>
      {createMutation.isError && (
        <p className="mt-2 text-xs text-red-400">
          {(createMutation.error as Error)?.message ?? "Failed to create instance"}
        </p>
      )}
    </div>
  )
}

export default function DeepLInstancesPage() {
  const { data: instances, isLoading } = useQuery({
    queryKey: ["deepl-instances"],
    queryFn: getDeepLInstances,
  })

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-zinc-400">
          Configure which language pairs DeepL should translate. All pairs share the API key
          set on the System Keys page. When a word is looked up in the reader, all enabled pairs
          matching the book&apos;s language are translated automatically.
        </p>
      </div>

      <AddInstanceForm />

      <div className="space-y-2">
        {isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
        ) : instances && instances.length > 0 ? (
          instances.map((instance) => (
            <InstanceRow key={instance.id} instance={instance} />
          ))
        ) : (
          <p className="text-sm text-zinc-600">No translation pairs configured yet.</p>
        )}
      </div>
    </div>
  )
}
