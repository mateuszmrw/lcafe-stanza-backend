"use client"

import { useRef, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Upload, RefreshCw } from "lucide-react"
import { getCognateStatus, uploadCognates } from "@/src/lib/api/admin"

export default function CognatesPage() {
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const { data: status, isLoading } = useQuery({
    queryKey: ["admin-cognate-status"],
    queryFn: getCognateStatus,
    refetchInterval: (query) =>
      query.state.data === undefined ? 5000 : false,
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadCognates(file),
    onSuccess: () => {
      setSelectedFile(null)
      if (fileRef.current) fileRef.current.value = ""
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["admin-cognate-status"] })
      }, 2000)
    },
  })

  const lastImported = status?.last_imported_at
    ? new Date(status.last_imported_at).toLocaleString()
    : "Never"

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-zinc-100">Cognate Pairs</h2>
        <p className="mt-1 text-sm text-zinc-400">
          Upload a tab-separated TSV file of cognate pairs for Polish ↔ Russian detection.
        </p>
      </div>

      {/* Status card */}
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 space-y-3">
        <h3 className="text-sm font-medium text-zinc-300">Current status</h3>
        {isLoading ? (
          <p className="text-sm text-zinc-500">Loading…</p>
        ) : (
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-zinc-500">Total pairs</p>
              <p className="text-zinc-100 font-medium">
                {status?.row_count.toLocaleString() ?? "—"}
              </p>
            </div>
            <div>
              <p className="text-zinc-500">Last imported</p>
              <p className="text-zinc-100 font-medium">{lastImported}</p>
            </div>
            {status?.pairs.map((p) => (
              <div key={p.l2}>
                <p className="text-zinc-500">Supported pairs</p>
                <p className="text-zinc-100 font-medium">
                  {p.l2.toUpperCase()} ↔ {p.l1_codes.map((c) => c.toUpperCase()).join(", ")}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upload card */}
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 space-y-4">
        <h3 className="text-sm font-medium text-zinc-300">Upload TSV file</h3>
        <p className="text-xs text-zinc-500">
          Expected columns (tab-separated, with header):{" "}
          <code className="rounded bg-zinc-800 px-1 py-0.5 font-mono text-zinc-300">
            l1_lemma · l1_language · l2_lemma · l2_language · cognate_type · similarity_score ·
            semantic_score · source · l1_meaning · l2_meaning
          </code>
        </p>

        <div className="flex items-center gap-3">
          <input
            ref={fileRef}
            type="file"
            accept=".tsv,.txt"
            onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
            className="block text-sm text-zinc-400 file:mr-3 file:rounded-md file:border-0 file:bg-zinc-700 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-zinc-200 hover:file:bg-zinc-600"
          />
          <button
            onClick={() => selectedFile && uploadMutation.mutate(selectedFile)}
            disabled={!selectedFile || uploadMutation.isPending}
            className="flex items-center gap-1.5 rounded-md bg-blue-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Upload className="h-4 w-4" />
            {uploadMutation.isPending ? "Uploading…" : "Upload"}
          </button>
        </div>

        {uploadMutation.isSuccess && (
          <div className="flex items-center gap-2 rounded-md border border-blue-800/50 bg-blue-950/30 px-4 py-3 text-sm text-blue-300">
            <RefreshCw className="h-4 w-4 animate-spin" />
            Import enqueued — row count will update when the worker finishes.
          </div>
        )}

        {uploadMutation.isError && (
          <div className="rounded-md border border-red-800/50 bg-red-950/30 px-4 py-3 text-sm text-red-300">
            {uploadMutation.error instanceof Error
              ? uploadMutation.error.message
              : "Upload failed. Please try again."}
          </div>
        )}
      </div>

    </div>
  )
}
