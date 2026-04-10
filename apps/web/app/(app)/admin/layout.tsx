"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useEffect, type ReactNode } from "react"
import { useAuth } from "@/src/stores/auth"
import { cn } from "@/src/lib/cn"

const TABS = [
  { href: "/admin/languages", label: "Languages" },
  { href: "/admin/providers", label: "Providers" },
  { href: "/admin/dictionary", label: "Dictionary" },
  { href: "/admin/frequencies", label: "Word Frequency" },
  { href: "/admin/system-keys", label: "System Keys" },
  { href: "/admin/llm", label: "LLM" },
  { href: "/admin/deepl-instances", label: "DeepL Instances" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/data", label: "Data" },
]

export default function AdminLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { user } = useAuth()

  useEffect(() => {
    if (user && user.is_admin === false) {
      router.replace("/library")
    }
  }, [user, router])

  if (!user?.is_admin) return null

  return (
    <div className="p-8">
      <h1 className="mb-6 text-2xl font-bold text-zinc-100">Admin</h1>

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

      <div className="max-w-4xl">{children}</div>
    </div>
  )
}
