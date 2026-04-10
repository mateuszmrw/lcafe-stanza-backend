"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { BarChart2, BookOpen, Library, LogOut, Settings, ShieldCheck, User } from "lucide-react"
import { cn } from "@/src/lib/cn"
import { useAuth } from "@/src/stores/auth"
import { logout } from "@/src/lib/api/auth"
import { LanguageSwitcher } from "./LanguageSwitcher"

const NAV_LINKS = [
  { href: "/library", label: "Library", icon: Library },
  { href: "/vocabulary", label: "Vocabulary", icon: BookOpen },
  { href: "/stats", label: "Statistics", icon: BarChart2 },
  { href: "/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, clearTokens } = useAuth()
  const isAdmin = user?.is_admin ?? false

  async function handleLogout() {
    try {
      await logout()
    } catch {
      // fire-and-forget; clear client state regardless
    }
    clearTokens()
    router.push("/login")
  }

  return (
    <aside className="flex h-screen w-60 flex-col bg-zinc-900 text-zinc-100">
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-5 border-b border-zinc-800">
        <BookOpen className="h-6 w-6 text-blue-400" />
        <span className="text-lg font-semibold tracking-tight">Slovo</span>
      </div>

      {/* Language switcher */}
      <div className="border-b border-zinc-800 py-3">
        <LanguageSwitcher />
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-1 px-3">
          {NAV_LINKS.map(({ href, label, icon: Icon }) => (
            <li key={href}>
              <Link
                href={href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  pathname.startsWith(href)
                    ? "bg-zinc-700 text-white"
                    : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            </li>
          ))}
          {isAdmin && (
            <li>
              <Link
                href="/admin"
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  pathname.startsWith("/admin")
                    ? "bg-zinc-700 text-white"
                    : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
                )}
              >
                <ShieldCheck className="h-4 w-4" />
                Admin
              </Link>
            </li>
          )}
        </ul>
      </nav>

      {/* User section */}
      <div className="border-t border-zinc-800 px-3 py-4">
        <div className="flex items-center gap-3 rounded-md px-3 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-700 text-xs font-medium text-zinc-200">
            {user?.username?.[0]?.toUpperCase() ?? <User className="h-4 w-4" />}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-zinc-200">
              {user?.username ?? "Account"}
            </p>
            <p className="truncate text-xs text-zinc-500">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="mt-1 flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100"
        >
          <LogOut className="h-4 w-4" />
          Log out
        </button>
      </div>
    </aside>
  )
}
