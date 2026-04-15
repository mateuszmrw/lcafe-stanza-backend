"use client"

import { useEffect, useState } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { CheckCircle, XCircle } from "lucide-react"
import { getAnkiSettings, updateAnkiSettings, testAnkiConnection } from "@/src/lib/api/anki"

export default function AdminAnkiPage() {
  const [url, setUrl] = useState("")
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [testing, setTesting] = useState(false)
  const [saved, setSaved] = useState(false)

  const { data: settings, isLoading } = useQuery({
    queryKey: ["admin-anki-settings"],
    queryFn: getAnkiSettings,
  })

  // Populate URL field when settings load
  useEffect(() => {
    if (settings) setUrl(settings.anki_connect_url ?? "")
  }, [settings])

  const saveMutation = useMutation({
    mutationFn: (newUrl: string) => updateAnkiSettings(newUrl || null),
    onSuccess: () => {
      setSaved(true)
      setTestResult(null)
      setTimeout(() => setSaved(false), 2000)
    },
  })

  async function handleTest() {
    setTesting(true)
    setTestResult(null)
    try {
      const result = await testAnkiConnection()
      setTestResult(result)
    } catch (err: unknown) {
      setTestResult({ success: false, message: err instanceof Error ? err.message : "Connection failed" })
    } finally {
      setTesting(false)
    }
  }

  if (isLoading) {
    return <div className="animate-pulse h-8 w-64 rounded bg-zinc-800" />
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="mb-1 text-base font-semibold text-zinc-100">AnkiConnect</h2>
        <p className="text-sm text-zinc-500">
          Set the AnkiConnect URL running on your host machine. Users can then sync their
          learning vocabulary directly to Anki. Decks are created as{" "}
          <code className="rounded bg-zinc-800 px-1 text-zinc-300">username/language</code>.
        </p>
      </div>

      <div className="space-y-3">
        <label className="block text-sm font-medium text-zinc-300">
          AnkiConnect URL
        </label>
        <div className="flex gap-2">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="http://localhost:8765"
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none placeholder:text-zinc-600 focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleTest}
            disabled={testing || !url}
            className="rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2 text-sm text-zinc-300 transition hover:bg-zinc-700 disabled:opacity-40"
          >
            {testing ? "Testing…" : "Test"}
          </button>
          <button
            onClick={() => saveMutation.mutate(url)}
            disabled={saveMutation.isPending}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
          >
            {saved ? "Saved!" : "Save"}
          </button>
        </div>

        {testResult && (
          <div className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${
            testResult.success
              ? "bg-emerald-900/30 text-emerald-400"
              : "bg-red-900/30 text-red-400"
          }`}>
            {testResult.success
              ? <CheckCircle className="h-4 w-4 shrink-0" />
              : <XCircle className="h-4 w-4 shrink-0" />}
            {testResult.message}
          </div>
        )}
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 text-sm text-zinc-400 space-y-2">
        <p className="font-medium text-zinc-300">Setup instructions</p>
        <ol className="list-decimal list-inside space-y-1">
          <li>Install the <span className="text-zinc-200">AnkiConnect</span> add-on in Anki (code: 2055492159)</li>
          <li>In Anki&apos;s AnkiConnect settings, add your Slovo server to <code className="text-zinc-300">webCorsOriginList</code></li>
          <li>The default URL is <code className="text-zinc-300">http://localhost:8765</code></li>
          <li>If Slovo runs in Docker, use your host IP instead of <code className="text-zinc-300">localhost</code></li>
        </ol>
        <p className="text-xs text-zinc-600">
          Current setting: {settings?.anki_connect_url ?? <em>not configured</em>}
        </p>
      </div>
    </div>
  )
}
