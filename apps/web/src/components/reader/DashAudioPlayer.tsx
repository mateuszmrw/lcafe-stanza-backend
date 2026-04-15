"use client"

import { useEffect, useRef, useCallback } from "react"
import { Play, Pause, Volume2, VolumeX } from "lucide-react"
import * as dashjs from "dashjs"
import { useAudioPlayerStore } from "@/src/stores/audioPlayer"
import { ttsDashManifestUrl, getAccessToken } from "@/src/lib/api/audio"

interface DashAudioPlayerProps {
  bookId: string
  pageNumber: number
  onPageEnd?: () => void
}

function formatTime(ms: number): string {
  const s = Math.floor(ms / 1000)
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${sec.toString().padStart(2, "0")}`
}

export function DashAudioPlayer({ bookId, pageNumber, onPageEnd }: DashAudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const playerRef = useRef<dashjs.MediaPlayerClass | null>(null)
  const { isPlaying, currentTimeMs, alignments, play, pause, tick } = useAudioPlayerStore()

  // Initialise / re-initialise dash.js whenever page changes
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const player = dashjs.MediaPlayer().create()

    // Add auth token to every segment request
    const token = getAccessToken()
    if (token) {
      player.extend(
        "RequestModifier",
        () => ({
          modifyRequestHeader: (xhr: XMLHttpRequest) => {
            xhr.setRequestHeader("Authorization", `Bearer ${token}`)
            return xhr
          },
        }),
        true,
      )
    }

    player.initialize(audio, ttsDashManifestUrl(bookId, pageNumber), false)
    playerRef.current = player

    return () => {
      player.destroy()
      playerRef.current = null
    }
  }, [bookId, pageNumber])

  // Sync play/pause
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    if (isPlaying) {
      audio.play().catch(() => {})
    } else {
      audio.pause()
    }
  }, [isPlaying])

  const handleTimeUpdate = useCallback(() => {
    const audio = audioRef.current
    if (!audio) return
    const ms = Math.floor(audio.currentTime * 1000)
    tick(ms)

    if (onPageEnd && alignments.length > 0) {
      const last = alignments[alignments.length - 1]
      if (ms >= last.audio_end_ms) onPageEnd()
    }
  }, [tick, alignments, onPageEnd])

  const handleEnded = useCallback(() => pause(), [pause])

  const handleScrub = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current
    if (!audio) return
    const ms = Number(e.target.value)
    audio.currentTime = ms / 1000
    tick(ms)
  }

  const totalMs = audioRef.current ? Math.floor(audioRef.current.duration * 1000) : 0

  const toggleMute = () => {
    const audio = audioRef.current
    if (audio) audio.muted = !audio.muted
  }

  return (
    <div
      className="flex items-center gap-4 border-t border-zinc-800 bg-zinc-900 px-6 pt-3"
      style={{ paddingBottom: "calc(var(--sab) + 0.75rem)" }}
    >
      {/* dash.js attaches to an audio element — no src needed, player sets it */}
      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        preload="none"
      />

      <button
        onClick={() => (isPlaying ? pause() : play())}
        className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-white transition hover:bg-blue-500"
        aria-label={isPlaying ? "Pause" : "Play"}
      >
        {isPlaying ? (
          <Pause className="h-3.5 w-3.5" />
        ) : (
          <Play className="h-3.5 w-3.5 pl-0.5" />
        )}
      </button>

      <span className="w-10 text-right text-xs tabular-nums text-zinc-400">
        {formatTime(currentTimeMs)}
      </span>

      <input
        type="range"
        min={0}
        max={totalMs || 1}
        value={currentTimeMs}
        onChange={handleScrub}
        className="h-1 flex-1 cursor-pointer appearance-none rounded-full bg-zinc-700 accent-blue-500"
        aria-label="Seek"
      />

      <span className="w-10 text-xs tabular-nums text-zinc-500">
        {totalMs ? formatTime(totalMs) : "--:--"}
      </span>

      <button onClick={toggleMute} className="text-zinc-400 transition hover:text-zinc-200" aria-label="Toggle mute">
        {audioRef.current?.muted ? (
          <VolumeX className="h-4 w-4" />
        ) : (
          <Volume2 className="h-4 w-4" />
        )}
      </button>
    </div>
  )
}
