"use client"

import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, Key, Check, Trash2 } from "lucide-react"
import { listMyProviders, getApiKeyStatus, setApiKey, deleteApiKey } from "@/src/lib/api/users"
const PROVIDER_TYPE_LABELS: Record<string, string> = {
  translation: "Translation",
  dictionary: "Dictionary",
}

const PROVIDER_HINTS: Record<string, string> = {
  deepl: "Free-tier keys end with :fx (e.g. abc123:fx). Pro keys do not have this suffix.",
}

function ApiKeyCard({ slug, name, description, type }: {
  slug: string
  name: string
  description: string | null
  type: string
}) {
  const queryClient = useQueryClient()
  const [input, setInput] = useState("")
  const [editing, setEditing] = useState(false)

  const { data: status, isLoading } = useQuery({
    queryKey: ["api-key-status", slug],
    queryFn: () => getApiKeyStatus(slug),
    staleTime: 30_000,
  })

  const saveMutation = useMutation({
    mutationFn: () => setApiKey(slug, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-key-status", slug] })
      queryClient.invalidateQueries({ queryKey: ["translation-available"] })
      setInput("")
      setEditing(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteApiKey(slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-key-status", slug] })
      queryClient.invalidateQueries({ queryKey: ["translation-available"] })
    },
  })

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <Key className="h-4 w-4 text-zinc-500" />
            <span className="text-sm font-semibold text-zinc-200">{name}</span>
            <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-xs text-zinc-500">
              {PROVIDER_TYPE_LABELS[type] ?? type}
            </span>
          </div>
          {description && (
            <p className="mt-1 text-xs text-zinc-500">{description}</p>
          )}
        </div>
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-zinc-600" />
        ) : status?.exists ? (
          <span className="flex items-center gap-1 text-xs text-green-500">
            <Check className="h-3 w-3" /> Configured
          </span>
        ) : (
          <span className="text-xs text-zinc-600">Not configured</span>
        )}
      </div>

      {editing ? (
        <div className="space-y-2 mt-3">
          {PROVIDER_HINTS[slug] && (
            <p className="text-xs text-amber-400/80">{PROVIDER_HINTS[slug]}</p>
          )}
          <div className="flex gap-2">
            <input
              type="password"
              placeholder="Paste API key…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              autoFocus
              className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending || !input}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
            >
              {saveMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Save"}
            </button>
            <button
              onClick={() => { setEditing(false); setInput("") }}
              className="rounded-lg px-3 py-1.5 text-sm text-zinc-400 hover:bg-zinc-800"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="flex gap-2 mt-3">
          <button
            onClick={() => setEditing(true)}
            className="rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800 transition"
          >
            {status?.exists ? "Update key" : "Add key"}
          </button>
          {status?.exists && (
            <button
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-red-400 hover:bg-zinc-800 transition disabled:opacity-50"
            >
              {deleteMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Trash2 className="h-3.5 w-3.5" />
              )}
              Remove
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default function ApiKeysPage() {
  const { data: providers, isLoading } = useQuery({
    queryKey: ["admin-providers", "external"],
    queryFn: () => listMyProviders(),
    staleTime: 60_000,
  })

  const externalProviders = providers?.filter(
    (p) => !p.is_builtin && (p.type === "translation" || p.type === "dictionary")
  ) ?? []

  const builtinProviders = providers?.filter(
    (p) => p.is_builtin && (p.type === "translation" || p.type === "dictionary")
  ) ?? []

  if (isLoading) {
    return <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-zinc-400">
        Add your own API keys for external translation and dictionary services. Keys are encrypted and stored securely.
      </p>

      {externalProviders.length > 0 && (
        <div className="space-y-3">
          {externalProviders.map((p) => (
            <ApiKeyCard
              key={p.slug}
              slug={p.slug}
              name={p.name}
              description={p.description}
              type={p.type}
            />
          ))}
        </div>
      )}

      {builtinProviders.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
            Built-in Services
          </p>
          {builtinProviders.map((p) => (
            <div key={p.slug} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              <div className="flex items-center gap-2">
                <Key className="h-4 w-4 text-zinc-600" />
                <span className="text-sm font-medium text-zinc-400">{p.name}</span>
                <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-xs text-zinc-600">
                  {PROVIDER_TYPE_LABELS[p.type] ?? p.type}
                </span>
                <span className="ml-auto flex items-center gap-1 text-xs text-green-600">
                  <Check className="h-3 w-3" /> Built-in
                </span>
              </div>
              {p.description && (
                <p className="mt-1.5 text-xs text-zinc-600">{p.description}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {!isLoading && externalProviders.length === 0 && builtinProviders.length === 0 && (
        <p className="text-sm text-zinc-600">No external providers configured by the admin.</p>
      )}
    </div>
  )
}
