"use client"

import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, Key, Trash2, Database, Settings, Bot } from "lucide-react"
import {
  getLLMConfig,
  setLLMConfig,
  deleteLLMConfig,
  type LLMProviderStatus,
} from "@/src/lib/api/admin"

const MODELS: Record<string, string[]> = {
  openai: [
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-4o",
    "gpt-4o-mini",
  ],
}

const KEY_SOURCE_LABELS: Record<string, { label: string; color: string }> = {
  database: { label: "DB key set", color: "text-green-500" },
  env: { label: "Env var", color: "text-yellow-500" },
  none: { label: "Not configured", color: "text-zinc-600" },
}

function LLMProviderCard({ status }: { status: LLMProviderStatus }) {
  const queryClient = useQueryClient()
  const [editingKey, setEditingKey] = useState(false)
  const [keyInput, setKeyInput] = useState("")
  const [modelInput, setModelInput] = useState(status.model ?? "")

  const saveMutation = useMutation({
    mutationFn: (data: { api_key?: string; model?: string }) =>
      setLLMConfig(status.provider_slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-config"] })
      setEditingKey(false)
      setKeyInput("")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteLLMConfig(status.provider_slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-config"] })
    },
  })

  const keySourceInfo = KEY_SOURCE_LABELS[status.key_source] ?? KEY_SOURCE_LABELS.none
  const availableModels = MODELS[status.provider_slug] ?? []

  function handleSaveKey() {
    const data: { api_key?: string; model?: string } = { api_key: keyInput }
    if (modelInput) data.model = modelInput
    saveMutation.mutate(data)
  }

  function handleSaveModel() {
    saveMutation.mutate({ model: modelInput })
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-zinc-500" />
            <span className="text-sm font-semibold text-zinc-200">
              {status.provider.name}
            </span>
          </div>
          {status.provider.description && (
            <p className="mt-1 text-xs text-zinc-500">{status.provider.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {status.key_source === "database" ? (
            <Database className="h-3.5 w-3.5 text-green-500" />
          ) : status.key_source === "env" ? (
            <Settings className="h-3.5 w-3.5 text-yellow-500" />
          ) : null}
          <span className={`text-xs ${keySourceInfo.color}`}>{keySourceInfo.label}</span>
        </div>
      </div>

      {/* Env var hint */}
      {status.key_source === "env" && (
        <p className="rounded-lg bg-yellow-900/20 px-3 py-2 text-xs text-yellow-400">
          Key is set via environment variable. Setting a DB key will take precedence.
        </p>
      )}

      {/* API key section */}
      <div>
        <p className="text-xs font-medium text-zinc-400 mb-2">API Key</p>
        {editingKey ? (
          <div className="space-y-2">
            <div className="flex gap-2">
              <input
                type="password"
                placeholder="Paste API key…"
                value={keyInput}
                onChange={(e) => setKeyInput(e.target.value)}
                autoFocus
                className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleSaveKey}
                disabled={saveMutation.isPending || !keyInput}
                className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
              >
                {saveMutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  "Save"
                )}
              </button>
              <button
                onClick={() => { setEditingKey(false); setKeyInput("") }}
                className="rounded-lg px-3 py-1.5 text-sm text-zinc-400 hover:bg-zinc-800"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={() => setEditingKey(true)}
              className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800 transition"
            >
              <Key className="h-3.5 w-3.5" />
              {status.key_source === "database" ? "Update key" : "Set key"}
            </button>
            {status.key_source === "database" && (
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
                Remove key
              </button>
            )}
          </div>
        )}
      </div>

      {/* Model section */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-medium text-zinc-400">Model</p>
          <span className="text-xs text-zinc-600">
            source: {status.model_source}
          </span>
        </div>
        <div className="flex gap-2">
          <select
            value={modelInput}
            onChange={(e) => setModelInput(e.target.value)}
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
          >
            {availableModels.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <button
            onClick={handleSaveModel}
            disabled={
              saveMutation.isPending ||
              !modelInput ||
              modelInput === status.model ||
              status.key_source === "none"
            }
            className="rounded-lg bg-zinc-700 px-3 py-1.5 text-sm font-medium text-zinc-200 hover:bg-zinc-600 disabled:opacity-40 transition"
          >
            {saveMutation.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              "Apply"
            )}
          </button>
        </div>
        {status.key_source === "none" && (
          <p className="mt-1.5 text-xs text-zinc-600">
            Set an API key first to configure the model in the database.
          </p>
        )}
      </div>
    </div>
  )
}

export default function AdminLLMPage() {
  const { data: llmConfig, isLoading } = useQuery({
    queryKey: ["llm-config"],
    queryFn: getLLMConfig,
  })

  if (isLoading) {
    return <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-zinc-400">
        Configure LLM providers used for grammar explanations. Keys are shared
        across all users — only admins can set them.
      </p>
      <p className="text-xs text-zinc-600">
        Priority: System DB key → Environment variable
      </p>

      {llmConfig?.map((s) => (
        <LLMProviderCard key={s.provider_slug} status={s} />
      ))}

      {!isLoading && !llmConfig?.length && (
        <p className="text-sm text-zinc-600">No LLM providers available.</p>
      )}
    </div>
  )
}
