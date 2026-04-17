"use client"

import { useState } from "react"
import { Upload, Video, Globe } from "lucide-react"
import { Dialog } from "@/src/components/ui/Dialog"
import { cn } from "@/src/lib/cn"
import { BookTab } from "./tabs/BookTab"
import { YouTubeTab } from "./tabs/YouTubeTab"
import { WebsiteTab } from "./tabs/WebsiteTab"

interface ImportBookDialogProps {
  open: boolean
  onClose: () => void
}

type Tab = "book" | "youtube" | "website"

export function ImportBookDialog({ open, onClose }: ImportBookDialogProps) {
  const [tab, setTab] = useState<Tab>("book")

  function handleClose() {
    onClose()
    setTimeout(() => setTab("book"), 200)
  }

  return (
    <Dialog open={open} onClose={handleClose} title="Import Content">
      <div className="mb-5 flex rounded-lg border border-zinc-800 bg-zinc-800/50 p-0.5">
        <TabButton active={tab === "book"} onClick={() => setTab("book")}>
          <Upload className="h-3.5 w-3.5" />
          Book / EPUB
        </TabButton>
        <TabButton active={tab === "youtube"} onClick={() => setTab("youtube")}>
          <Video className="h-3.5 w-3.5" />
          YouTube
        </TabButton>
        <TabButton active={tab === "website"} onClick={() => setTab("website")}>
          <Globe className="h-3.5 w-3.5" />
          Website
        </TabButton>
      </div>

      {tab === "book" ? (
        <BookTab onClose={handleClose} />
      ) : tab === "youtube" ? (
        <YouTubeTab onClose={handleClose} />
      ) : (
        <WebsiteTab onClose={handleClose} />
      )}
    </Dialog>
  )
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-1 items-center justify-center gap-1.5 rounded-md py-1.5 text-sm font-medium transition",
        active
          ? "bg-zinc-700 text-zinc-100 shadow-sm"
          : "text-zinc-400 hover:text-zinc-200"
      )}
    >
      {children}
    </button>
  )
}
