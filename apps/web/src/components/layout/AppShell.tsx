"use client"

import { useState } from "react"
import type { ReactNode } from "react"
import { Menu } from "lucide-react"
import { Sidebar } from "./Sidebar"

export function AppShell({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex h-[100dvh] overflow-hidden bg-zinc-950 text-zinc-100">
      {/* Desktop sidebar — hidden below lg */}
      <div className="hidden lg:block shrink-0">
        <Sidebar />
      </div>

      {/* Mobile/tablet sidebar overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/70"
            onClick={() => setSidebarOpen(false)}
          />
          {/* Sidebar panel */}
          <div className="relative z-10 h-full w-64 shadow-2xl">
            <Sidebar onClose={() => setSidebarOpen(false)} />
          </div>
        </div>
      )}

      {/* Main content */}
      <main className="relative flex-1 overflow-y-auto min-w-0">
        {/* Mobile hamburger — floats top-left, hidden on lg+ */}
        <button
          onClick={() => setSidebarOpen(true)}
          aria-label="Open menu"
          className="fixed left-3 top-3 z-30 flex items-center justify-center rounded-lg bg-zinc-900/90 p-2.5 text-zinc-400 shadow-lg backdrop-blur-sm lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>

        {children}
      </main>
    </div>
  )
}
