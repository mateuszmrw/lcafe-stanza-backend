"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2 } from "lucide-react"
import { listAdminProviders, updateAdminProvider, type ProviderAdminResponse } from "@/src/lib/api/admin"
import { cn } from "@/src/lib/cn"

const TYPE_COLORS: Record<string, string> = {
  nlp: "text-purple-400 bg-purple-900/30",
  translation: "text-blue-400 bg-blue-900/30",
  dictionary: "text-green-400 bg-green-900/30",
}

function ProviderRow({ provider }: { provider: ProviderAdminResponse }) {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (is_active: boolean) =>
      updateAdminProvider(provider.id, { is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-providers"] })
    },
  })

  return (
    <tr className="border-b border-zinc-800 hover:bg-zinc-900/50">
      <td className="py-3 px-4">
        <p className="text-sm font-medium text-zinc-200">{provider.name}</p>
        {provider.description && (
          <p className="text-xs text-zinc-500 mt-0.5">{provider.description}</p>
        )}
      </td>
      <td className="py-3 px-4 text-sm font-mono text-zinc-500">{provider.slug}</td>
      <td className="py-3 px-4">
        <span className={cn(
          "rounded-full px-2 py-0.5 text-xs font-medium",
          TYPE_COLORS[provider.type] ?? "text-zinc-400 bg-zinc-800"
        )}>
          {provider.type}
        </span>
      </td>
      <td className="py-3 px-4">
        {provider.is_builtin ? (
          <span className="text-xs text-zinc-600">Built-in</span>
        ) : (
          <button
            onClick={() => mutation.mutate(!provider.is_active)}
            disabled={mutation.isPending}
            className={cn(
              "relative inline-flex h-5 w-9 items-center rounded-full transition-colors disabled:opacity-50",
              provider.is_active ? "bg-blue-600" : "bg-zinc-700"
            )}
            aria-label={provider.is_active ? "Disable" : "Enable"}
          >
            <span
              className={cn(
                "inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform",
                provider.is_active ? "translate-x-4.5" : "translate-x-0.5"
              )}
            />
          </button>
        )}
      </td>
    </tr>
  )
}

export default function AdminProvidersPage() {
  const { data: providers, isLoading } = useQuery({
    queryKey: ["admin-providers"],
    queryFn: () => listAdminProviders(),
  })

  if (isLoading) {
    return <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
  }

  return (
    <div>
      <p className="mb-4 text-sm text-zinc-400">
        Manage NLP, translation, and dictionary providers. Built-in providers cannot be disabled from this panel.
      </p>
      <div className="rounded-xl border border-zinc-800 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900">
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Provider</th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Slug</th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Type</th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Active</th>
            </tr>
          </thead>
          <tbody className="bg-zinc-950">
            {providers?.map((p) => (
              <ProviderRow key={p.id} provider={p} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
