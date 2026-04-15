"use client"

import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, Settings2, X } from "lucide-react"
import {
  listAdminLanguages,
  listAdminProviders,
  updateAdminLanguage,
  getNlpConfig,
  setNlpConfig,
  setReaderConfig,
  type LanguageAdminResponse,
} from "@/src/lib/api/admin"
import { READER_CONFIG_DEFAULTS, READER_CONFIG_LABELS, type ReaderConfig } from "@/src/lib/api/languages"
import { cn } from "@/src/lib/cn"

function NlpConfigModal({
  lang,
  onClose,
}: {
  lang: LanguageAdminResponse
  onClose: () => void
}) {
  const queryClient = useQueryClient()

  const { data: nlpProviders } = useQuery({
    queryKey: ["admin-providers", "nlp"],
    queryFn: () => listAdminProviders("nlp"),
    staleTime: 60_000,
  })

  const { data: currentConfig, isLoading: configLoading } = useQuery({
    queryKey: ["nlp-config", lang.id],
    queryFn: () => getNlpConfig(lang.id),
  })

  const [selectedProvider, setSelectedProvider] = useState<string>("")
  const [configJson, setConfigJson] = useState<string>("")
  const [jsonError, setJsonError] = useState("")

  useEffect(() => {
    if (currentConfig) {
      setSelectedProvider(currentConfig.provider_id)
      setConfigJson(JSON.stringify(currentConfig.config, null, 2))
    }
  }, [currentConfig])

  const saveMutation = useMutation({
    mutationFn: () => {
      let parsed: Record<string, unknown>
      try {
        parsed = JSON.parse(configJson)
      } catch {
        throw new Error("Invalid JSON")
      }
      return setNlpConfig(lang.id, selectedProvider, parsed)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["nlp-config", lang.id] })
      onClose()
    },
    onError: (e: unknown) => {
      setJsonError(e instanceof Error ? e.message : "Failed to save")
    },
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-md rounded-xl border border-zinc-700 bg-zinc-900 p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold text-zinc-100">
            NLP Config — {lang.name}
          </h3>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
            <X className="h-4 w-4" />
          </button>
        </div>

        {configLoading ? (
          <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-zinc-500 mb-1.5">NLP Provider</label>
              <select
                value={selectedProvider}
                onChange={(e) => setSelectedProvider(e.target.value)}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select provider…</option>
                {nlpProviders?.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-zinc-500 mb-1.5">Config (JSON)</label>
              <p className="mb-1.5 text-xs text-zinc-600">
                For Stanza: <code className="text-zinc-500">{`{"stanza_language_name": "english"}`}</code>
              </p>
              <textarea
                value={configJson}
                onChange={(e) => { setConfigJson(e.target.value); setJsonError("") }}
                rows={5}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm font-mono text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
              />
              {jsonError && <p className="mt-1 text-xs text-red-400">{jsonError}</p>}
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={onClose}
                className="rounded-lg px-4 py-2 text-sm text-zinc-400 hover:bg-zinc-800"
              >
                Cancel
              </button>
              <button
                onClick={() => saveMutation.mutate()}
                disabled={saveMutation.isPending || !selectedProvider}
                className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
              >
                {saveMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Save
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function ReaderConfigModal({
  lang,
  onClose,
}: {
  lang: LanguageAdminResponse
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const merged: ReaderConfig = { ...READER_CONFIG_DEFAULTS, ...lang.reader_config }
  const [cfg, setCfg] = useState<ReaderConfig>(merged)

  const saveMutation = useMutation({
    mutationFn: () => setReaderConfig(lang.id, cfg),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-languages"] })
      onClose()
    },
  })

  const toggle = (key: keyof ReaderConfig) =>
    setCfg((prev) => ({ ...prev, [key]: !prev[key] }))

  const fields = Object.keys(READER_CONFIG_LABELS) as (keyof ReaderConfig)[]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-sm rounded-xl border border-zinc-700 bg-zinc-900 p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold text-zinc-100">
            Reader Panel — {lang.name}
          </h3>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="mb-4 text-xs text-zinc-500">
          Choose which NLP fields are shown in the reader definition panel for this language.
        </p>

        <div className="space-y-3">
          {fields.map((key) => (
            <label key={key} className="flex items-center justify-between gap-3 cursor-pointer group">
              <span className="text-sm text-zinc-300 group-hover:text-zinc-100 transition">
                {READER_CONFIG_LABELS[key]}
              </span>
              <button
                type="button"
                role="switch"
                aria-checked={cfg[key]}
                onClick={() => toggle(key)}
                className={cn(
                  "relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors",
                  cfg[key] ? "bg-blue-600" : "bg-zinc-700"
                )}
              >
                <span
                  className={cn(
                    "inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform",
                    cfg[key] ? "translate-x-4.5" : "translate-x-0.5"
                  )}
                />
              </button>
            </label>
          ))}
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm text-zinc-400 hover:bg-zinc-800"
          >
            Cancel
          </button>
          <button
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
          >
            {saveMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Save
          </button>
        </div>
      </div>
    </div>
  )
}

function LanguageRow({ lang }: { lang: LanguageAdminResponse }) {
  const queryClient = useQueryClient()
  const [nlpOpen, setNlpOpen] = useState(false)
  const [readerOpen, setReaderOpen] = useState(false)

  const toggleMutation = useMutation({
    mutationFn: (is_active: boolean) =>
      updateAdminLanguage(lang.id, { is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-languages"] })
    },
  })

  return (
    <>
      <tr className="border-b border-zinc-800 hover:bg-zinc-900/50">
        <td className="py-3 px-4 text-sm text-zinc-200">
          <span className="mr-2">{lang.flag_emoji}</span>
          {lang.name}
        </td>
        <td className="py-3 px-4 text-sm text-zinc-500 font-mono">{lang.code}</td>
        <td className="py-3 px-4">
          <button
            onClick={() => toggleMutation.mutate(!lang.is_active)}
            disabled={toggleMutation.isPending}
            className={cn(
              "relative inline-flex h-5 w-9 items-center rounded-full transition-colors disabled:opacity-50",
              lang.is_active ? "bg-blue-600" : "bg-zinc-700"
            )}
            aria-label={lang.is_active ? "Disable" : "Enable"}
          >
            <span
              className={cn(
                "inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform",
                lang.is_active ? "translate-x-4.5" : "translate-x-0.5"
              )}
            />
          </button>
        </td>
        <td className="py-3 px-4">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setNlpOpen(true)}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-zinc-400 hover:bg-zinc-800 transition"
            >
              <Settings2 className="h-3.5 w-3.5" />
              NLP
            </button>
            <button
              onClick={() => setReaderOpen(true)}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-zinc-400 hover:bg-zinc-800 transition"
            >
              <Settings2 className="h-3.5 w-3.5" />
              Reader
            </button>
          </div>
        </td>
      </tr>
      {nlpOpen && <NlpConfigModal lang={lang} onClose={() => setNlpOpen(false)} />}
      {readerOpen && <ReaderConfigModal lang={lang} onClose={() => setReaderOpen(false)} />}
    </>
  )
}

export default function AdminLanguagesPage() {
  const { data: languages, isLoading } = useQuery({
    queryKey: ["admin-languages"],
    queryFn: listAdminLanguages,
  })

  if (isLoading) {
    return <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
  }

  return (
    <div>
      <p className="mb-4 text-sm text-zinc-400">
        Enable or disable languages and configure their NLP pipeline (provider + parameters).
      </p>
      <div className="rounded-xl border border-zinc-800 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900">
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Language</th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Code</th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Active</th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">NLP Config</th>
            </tr>
          </thead>
          <tbody className="bg-zinc-950">
            {languages?.map((lang) => (
              <LanguageRow key={lang.id} lang={lang} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
