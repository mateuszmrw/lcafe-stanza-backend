"use client"

import { useQuery } from "@tanstack/react-query"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts"
import { Loader2 } from "lucide-react"
import { useAuth } from "@/src/stores/auth"
import { listLanguages } from "@/src/lib/api/languages"
import { getStats } from "@/src/lib/api/stats"
import { getCalendar, type CalendarEntry } from "@/src/lib/api/activity"
import { useState, useEffect, useRef } from "react"

const STATUS_COLORS: Record<string, string> = {
  new: "#3b82f6",
  learning: "#eab308",
  known: "#22c55e",
  well_known: "#16a34a",
  ignored: "#71717a",
}

const STATUS_LABELS: Record<string, string> = {
  new: "New",
  learning: "Learning",
  known: "Known",
  well_known: "Well known",
  ignored: "Ignored",
}

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

function cellColor(pages: number): string {
  if (pages === 0) return "bg-zinc-800"
  if (pages < 5) return "bg-blue-900"
  if (pages < 10) return "bg-blue-600"
  return "bg-blue-400"
}

function ReadingHeatmap({ entries }: { entries: CalendarEntry[] }) {
  const [tooltip, setTooltip] = useState<{ label: string; x: number; y: number } | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const pageMap = new Map(entries.map((e) => [e.date, e.pages]))

  // Build 53 weeks ending today, each week starts Monday
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const dayOfWeek = today.getDay() // 0=Sun
  const offsetToMon = dayOfWeek === 0 ? 6 : dayOfWeek - 1
  // Last day in grid is the Sunday of current week
  const gridEnd = new Date(today)
  gridEnd.setDate(gridEnd.getDate() + (6 - offsetToMon))
  // Grid starts 52 weeks before the Monday of current week
  const gridStart = new Date(gridEnd)
  gridStart.setDate(gridStart.getDate() - 52 * 7 + 1)

  const weeks: Array<Array<{ date: string; pages: number; future: boolean }>> = []
  const cursor = new Date(gridStart)
  while (cursor <= gridEnd) {
    const week: Array<{ date: string; pages: number; future: boolean }> = []
    for (let d = 0; d < 7; d++) {
      const iso = cursor.toISOString().slice(0, 10)
      week.push({ date: iso, pages: pageMap.get(iso) ?? 0, future: cursor > today })
      cursor.setDate(cursor.getDate() + 1)
    }
    weeks.push(week)
  }

  // Month label: show month name at the first week that starts in a new month
  function monthLabel(wi: number): string {
    const cell = weeks[wi]?.[0]
    if (!cell) return ""
    const d = new Date(cell.date + "T00:00:00")
    if (d.getDate() <= 7) {
      return d.toLocaleString("en", { month: "short" })
    }
    return ""
  }

  return (
    <div ref={containerRef} className="relative overflow-x-auto">
      <div className="flex gap-0.5 min-w-max">
        {/* Day-of-week labels */}
        <div className="flex flex-col gap-0.5 mr-1">
          <div className="h-4" />
          {DAY_LABELS.map((d, i) => (
            <div key={d} className={`h-3 text-[9px] leading-3 text-zinc-600 flex items-center ${i % 2 !== 0 ? "invisible" : ""}`}>
              {d}
            </div>
          ))}
        </div>

        {/* Weeks */}
        {weeks.map((week, wi) => (
          <div key={wi} className="flex flex-col gap-0.5">
            <div className="h-4 text-[9px] text-zinc-500 leading-4">{monthLabel(wi)}</div>
            {week.map((cell, di) => (
              <div
                key={di}
                className={`h-3 w-3 rounded-sm ${cell.future ? "opacity-0" : cellColor(cell.pages)}`}
                onMouseEnter={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect()
                  const d = new Date(cell.date + "T00:00:00")
                  const label = cell.pages > 0
                    ? `${cell.pages} page${cell.pages === 1 ? "" : "s"} · ${d.toLocaleDateString("en", { month: "short", day: "numeric" })}`
                    : d.toLocaleDateString("en", { month: "short", day: "numeric" })
                  setTooltip({ label, x: rect.left + rect.width / 2, y: rect.top })
                }}
                onMouseLeave={() => setTooltip(null)}
              />
            ))}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-3 flex items-center gap-1.5 text-xs text-zinc-500">
        <span>Less</span>
        {[0, 1, 5, 10].map((n) => (
          <div key={n} className={`h-3 w-3 rounded-sm ${cellColor(n)}`} />
        ))}
        <span>More</span>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="pointer-events-none fixed z-50 -translate-x-1/2 -translate-y-full -mt-1 rounded bg-zinc-700 px-2 py-1 text-xs text-zinc-100 shadow-lg"
          style={{ left: tooltip.x, top: tooltip.y - 6 }}
        >
          {tooltip.label}
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-zinc-100">{value}</p>
    </div>
  )
}

function CoverageBar({ label, value }: { label: string; value: number | null }) {
  if (value === null) return null
  const pct = Math.round(value * 100)
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-zinc-400">
        <span>{label}</span>
        <span>{pct}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-800">
        <div
          className="h-full rounded-full bg-blue-500 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export default function StatsPage() {
  const { activeLanguage } = useAuth()
  const [selectedLangCode, setSelectedLangCode] = useState<string>("")

  const { data: languages } = useQuery({
    queryKey: ["languages"],
    queryFn: listLanguages,
  })

  useEffect(() => {
    if (!selectedLangCode && activeLanguage) {
      setSelectedLangCode(activeLanguage.code)
    }
  }, [activeLanguage, selectedLangCode])

  const langCode = selectedLangCode || activeLanguage?.code || ""
  const selectedLang = languages?.find((l) => l.code === langCode)

  const { data: stats, isLoading, isError } = useQuery({
    queryKey: ["stats", langCode],
    queryFn: () => getStats(langCode),
    enabled: !!langCode,
  })

  const { data: calendarData } = useQuery({
    queryKey: ["activity-calendar", selectedLang?.id],
    queryFn: () => getCalendar(selectedLang!.id),
    enabled: !!selectedLang?.id,
    staleTime: 60_000,
  })

  const totalKnown =
    (stats?.word_counts["known"] ?? 0) + (stats?.word_counts["well_known"] ?? 0)

  const pieData = Object.entries(stats?.word_counts ?? {})
    .filter(([, v]) => v > 0)
    .map(([status, value]) => ({
      name: STATUS_LABELS[status] ?? status,
      value,
      color: STATUS_COLORS[status] ?? "#a1a1aa",
    }))

  const hasCoverage =
    stats?.frequency_coverage.top_1k !== null ||
    stats?.frequency_coverage.top_5k !== null ||
    stats?.frequency_coverage.top_10k !== null

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-zinc-100">Statistics</h1>
        <select
          value={selectedLangCode}
          onChange={(e) => setSelectedLangCode(e.target.value)}
          className="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
        >
          {languages?.map((l) => (
            <option key={l.code} value={l.code}>
              {l.flag_emoji ? `${l.flag_emoji} ` : ""}{l.name}
            </option>
          ))}
        </select>
      </div>

      {isLoading && (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-zinc-500" />
        </div>
      )}

      {isError && (
        <p className="rounded-lg bg-red-900/30 px-4 py-3 text-sm text-red-400">
          Failed to load statistics.
        </p>
      )}

      {stats && (
        <>
          {/* Reading heatmap */}
          {calendarData !== undefined && (
            <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-zinc-400">
                Reading activity
              </h2>
              <ReadingHeatmap entries={calendarData} />
            </section>
          )}

          {/* Counter cards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Total known" value={totalKnown.toLocaleString()} />
            <StatCard label="Books" value={stats.books_total} />
            <StatCard label="Pages read" value={stats.pages_read.toLocaleString()} />
            <StatCard
              label="Top-5k coverage"
              value={
                stats.frequency_coverage.top_5k !== null
                  ? `${Math.round(stats.frequency_coverage.top_5k * 100)}%`
                  : "—"
              }
            />
          </div>

          {/* Known words over time */}
          {stats.known_over_time.length > 0 && (
            <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-zinc-400">
                Known words over time
              </h2>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={stats.known_over_time}>
                  <XAxis
                    dataKey="date"
                    tick={{ fill: "#71717a", fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v: string) => v.slice(5)}
                  />
                  <YAxis
                    tick={{ fill: "#71717a", fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    width={40}
                  />
                  <Tooltip
                    contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8 }}
                    labelStyle={{ color: "#a1a1aa", fontSize: 12 }}
                    itemStyle={{ color: "#22c55e" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="known_cumulative"
                    name="Known"
                    stroke="#22c55e"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </section>
          )}

          {/* Status distribution */}
          {pieData.length > 0 && (
            <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-zinc-400">
                Word status distribution
              </h2>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    dataKey="value"
                    paddingAngle={2}
                  >
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Legend
                    formatter={(value: string) => (
                      <span style={{ color: "#a1a1aa", fontSize: 12 }}>{value}</span>
                    )}
                  />
                  <Tooltip
                    contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8 }}
                    labelStyle={{ color: "#a1a1aa", fontSize: 12 }}
                    itemStyle={{ color: "#e4e4e7" }}
                    formatter={(value) => [typeof value === "number" ? value.toLocaleString() : value, ""]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </section>
          )}

          {/* Frequency coverage */}
          {hasCoverage && (
            <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
              <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-zinc-400">
                Frequency coverage
              </h2>
              <p className="mb-4 text-xs text-zinc-500">
                % of the most common words you know
              </p>
              <div className="space-y-3">
                <CoverageBar label="Top 1,000" value={stats.frequency_coverage.top_1k} />
                <CoverageBar label="Top 5,000" value={stats.frequency_coverage.top_5k} />
                <CoverageBar label="Top 10,000" value={stats.frequency_coverage.top_10k} />
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}
