"use client"

import { useEffect, useRef, useCallback } from "react"
import { Play, Pause, Volume2, VolumeX } from "lucide-react"
import { useAudioPlayerStore } from "@/src/stores/audioPlayer"
import { audioStreamUrl } from "@/src/lib/api/audio"
import { getAudioProgress, saveAudioProgress } from "@/src/lib/reading-progress"

interface AudioPlayerProps {
  bookId: string
  totalDurationMs?: number | null
  onPageEnd?: () => void
}

function formatTime(ms: number): string {
  const totalSec = Math.floor(ms / 1000)
  const h = Math.floor(totalSec / 3600)
  const m = Math.floor((totalSec % 3600) / 60)
  const s = totalSec % 60
  if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
  return `${m}:${s.toString().padStart(2, "0")}`
}

export function AudioPlayer({ bookId, totalDurationMs, onPageEnd }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const currentSrcFileRef = useRef<string | null>(null)
  const saveTickRef = useRef(0)

  const {
    isPlaying,
    currentTimeMs,
    alignments,
    currentAudioFile,
    seekTarget,
    play,
    pause,
    tick,
    clearSeekTarget,
  } = useAudioPlayerStore()

  // Build the URL for a given file path (or book default)
  const buildSrc = useCallback(
    (filePath: string | null) => audioStreamUrl(bookId, filePath),
    [bookId]
  )

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

  // Switch audio file when currentAudioFile changes (new page alignments loaded)
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    if (currentSrcFileRef.current === currentAudioFile) return

    currentSrcFileRef.current = currentAudioFile
    const newSrc = buildSrc(currentAudioFile)
    audio.src = newSrc

    if (isPlaying && alignments.length > 0) {
      const startMs = alignments[0].audio_start_ms
      audio.addEventListener(
        "loadedmetadata",
        () => {
          audio.currentTime = startMs / 1000
          tick(startMs)
          audio.play().catch(() => {})
        },
        { once: true }
      )
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentAudioFile])

  // Handle explicit seek requests (e.g. from clicking a sentence)
  useEffect(() => {
    if (!seekTarget) return
    const audio = audioRef.current
    if (!audio) return

    const targetFile = seekTarget.audioFile
    const doSeek = () => {
      audio.currentTime = seekTarget.ms / 1000
      tick(seekTarget.ms)
    }

    if (targetFile !== currentSrcFileRef.current) {
      currentSrcFileRef.current = targetFile
      audio.src = buildSrc(targetFile)
      audio.addEventListener("loadedmetadata", doSeek, { once: true })
      if (isPlaying) {
        audio.addEventListener("loadedmetadata", () => audio.play().catch(() => {}), { once: true })
      }
    } else {
      doSeek()
    }

    clearSeekTarget()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seekTarget])

  // Restore saved audio position on first load
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    const saved = getAudioProgress(bookId)
    if (!saved) return

    const doRestore = () => {
      audio.currentTime = saved.timeMs / 1000
      tick(saved.timeMs)
    }
    audio.addEventListener("loadedmetadata", doRestore, { once: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookId])

  const handleTimeUpdate = useCallback(() => {
    const audio = audioRef.current
    if (!audio) return
    const ms = Math.floor(audio.currentTime * 1000)
    tick(ms)

    // Save audio progress every ~10 ticks (~2-3 seconds)
    saveTickRef.current++
    if (saveTickRef.current >= 10) {
      saveTickRef.current = 0
      saveAudioProgress(bookId, ms, currentSrcFileRef.current)
    }

    if (onPageEnd && alignments.length > 0) {
      const lastAlignment = alignments[alignments.length - 1]
      if (ms >= lastAlignment.audio_end_ms) {
        onPageEnd()
      }
    }
  }, [tick, alignments, onPageEnd, bookId])

  const handleEnded = useCallback(() => {
    pause()
    saveAudioProgress(bookId, 0, currentSrcFileRef.current)
  }, [pause, bookId])

  const handleScrub = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current
    if (!audio) return
    const ms = Number(e.target.value)
    audio.currentTime = ms / 1000
    tick(ms)
  }

  const totalMs = audioRef.current?.duration
    ? Math.floor(audioRef.current.duration * 1000)
    : 0
  const displayTotal = totalDurationMs ?? totalMs

  const toggleMute = () => {
    const audio = audioRef.current
    if (!audio) return
    audio.muted = !audio.muted
  }

  return (
    <div className="flex items-center gap-4 border-t border-zinc-800 bg-zinc-900 px-6 py-3">
      <audio
        ref={audioRef}
        src={buildSrc(null)}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        preload="metadata"
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

      <span className="w-16 text-xs tabular-nums text-zinc-500">
        {displayTotal ? formatTime(displayTotal) : "--:--"}
      </span>

      <button
        onClick={toggleMute}
        className="text-zinc-400 transition hover:text-zinc-200"
        aria-label="Toggle mute"
      >
        {audioRef.current?.muted ? (
          <VolumeX className="h-4 w-4" />
        ) : (
          <Volume2 className="h-4 w-4" />
        )}
      </button>
    </div>
  )
}
