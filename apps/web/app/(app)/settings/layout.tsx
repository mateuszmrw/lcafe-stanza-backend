"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import type { ReactNode } from "react"
import { cn } from "@/src/lib/cn"

const TABS = [
  { href: "/settings/profile", label: "Profile" },
  { href: "/settings/api-keys", label: "API Keys" },
  { href: "/settings/data", label: "Data" },
]

export default function SettingsLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname()

  return (
    <div className="p-8">
      <h1 className="mb-6 text-2xl font-bold text-zinc-100">Settings</h1>

      <div className="flex gap-1 border-b border-zinc-800 mb-8">
        {TABS.map((tab) => (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
              pathname === tab.href
                ? "border-blue-500 text-white"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      <div className="max-w-xl">{children}</div>
    </div>
  )
}
