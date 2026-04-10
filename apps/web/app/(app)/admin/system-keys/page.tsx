"use client"

import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, Key, Check, Trash2, Database, Settings } from "lucide-react"
import {
  getSystemKeys,
  setSystemKey,
  deleteSystemKey,
  type SystemKeyStatus,
} from "@/src/lib/api/admin"

const SOURCE_LABELS: Record<string, { label: string; color: string }> = {
  database: { label: "DB key set", color: "text-green-500" },
  env: { label: "Env var", color: "text-yellow-500" },
  none: { label: "Not configured", color: "text-zinc-600" },
}

function SystemKeyCard({ keyStatus }: { keyStatus: SystemKeyStatus }) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [input, setInput] = useState("")

  const saveMutation = useMutation({
    mutationFn: () => setSystemKey(keyStatus.provider_slug, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system-keys"] })
      setEditing(false)
      setInput("")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteSystemKey(keyStatus.provider_slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system-keys"] })
    },
  })

  const sourceInfo = SOURCE_LABELS[keyStatus.source] ?? SOURCE_LABELS.none

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <Key className="h-4 w-4 text-zinc-500" />
            <span className="text-sm font-semibold text-zinc-200">{keyStatus.provider.name}</span>
          </div>
          {keyStatus.provider.description && (
            <p className="mt-1 text-xs text-zinc-500">{keyStatus.provider.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {keyStatus.source === "database" ? (
            <Database className="h-3.5 w-3.5 text-green-500" />
          ) : keyStatus.source === "env" ? (
            <Settings className="h-3.5 w-3.5 text-yellow-500" />
          ) : null}
          <span className={`text-xs ${sourceInfo.color}`}>{sourceInfo.label}</span>
        </div>
      </div>

      {keyStatus.source === "env" && (
        <p className="mb-3 rounded-lg bg-yellow-900/20 px-3 py-2 text-xs text-yellow-400">
          Key is set via environment variable. Setting a DB key will take precedence.
        </p>
      )}

      {editing ? (
        <div className="space-y-2">
          {keyStatus.provider_slug === "deepl" && (
            <p className="text-xs text-amber-400/80">
              Free-tier keys end with <code>:fx</code> (e.g. <code>abc123:fx</code>). Pro keys do not.
            </p>
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
        <div className="flex gap-2">
          <button
            onClick={() => setEditing(true)}
            className="rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800 transition"
          >
            {keyStatus.source === "database" ? "Update key" : "Set key"}
          </button>
          {keyStatus.source === "database" && (
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

export default function AdminSystemKeysPage() {
  const { data: systemKeys, isLoading } = useQuery({
    queryKey: ["system-keys"],
    queryFn: getSystemKeys,
  })

  if (isLoading) {
    return <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-zinc-400">
        System-level API keys are shared across all users as a fallback when no user-specific key is configured.
        Users can still override with their own keys from the Settings page.
      </p>
      <p className="text-xs text-zinc-600">
        Priority: User key → System DB key → Environment variable
      </p>

      {systemKeys?.map((k) => (
        <SystemKeyCard key={k.provider_slug} keyStatus={k} />
      ))}

      {!isLoading && !systemKeys?.length && (
        <p className="text-sm text-zinc-600">No translation providers available.</p>
      )}
    </div>
  )
}
