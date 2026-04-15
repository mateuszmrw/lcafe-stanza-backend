"use client"

import { useEffect, useRef } from "react"
import { useAudioPlayerStore } from "@/src/stores/audioPlayer"

declare global {
  interface Window {
    YT: {
      Player: new (
        el: HTMLElement,
        opts: {
          videoId: string
          playerVars?: Record<string, number>
          events?: {
            onReady?: () => void
            onStateChange?: (e: { data: number }) => void
          }
        }
      ) => YTPlayer
      PlayerState: { PLAYING: number; PAUSED: number; ENDED: number }
    }
    onYouTubeIframeAPIReady?: () => void
  }
}

interface YTPlayer {
  getCurrentTime(): number
  seekTo(seconds: number, allowSeekAhead: boolean): void
  destroy(): void
}

interface YouTubePlayerProps {
  videoId: string
}

export function YouTubePlayer({ videoId }: YouTubePlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const playerRef = useRef<YTPlayer | null>(null)
  const readyRef = useRef(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const { tick, seekTarget, clearSeekTarget } = useAudioPlayerStore()

  useEffect(() => {
    function createPlayer() {
      if (!containerRef.current) return
      readyRef.current = false
      playerRef.current = new window.YT.Player(containerRef.current, {
        videoId,
        playerVars: { autoplay: 0, controls: 1, rel: 0 },
        events: {
          onReady: () => {
            readyRef.current = true
          },
          onStateChange: (e) => {
            if (e.data === window.YT.PlayerState.PLAYING) {
              startPolling()
            } else {
              stopPolling()
            }
          },
        },
      })
    }

    if (window.YT?.Player) {
      createPlayer()
    } else {
      if (!document.getElementById("yt-iframe-api")) {
        const tag = document.createElement("script")
        tag.id = "yt-iframe-api"
        tag.src = "https://www.youtube.com/iframe_api"
        document.head.appendChild(tag)
      }
      window.onYouTubeIframeAPIReady = createPlayer
    }

    return () => {
      stopPolling()
      readyRef.current = false
      playerRef.current?.destroy()
      playerRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoId])

  // Handle seek requests from the store (e.g. sentence click, position restore)
  useEffect(() => {
    if (!seekTarget || !playerRef.current || !readyRef.current) return
    playerRef.current.seekTo(seekTarget.ms / 1000, true)
    clearSeekTarget()
  }, [seekTarget, clearSeekTarget])

  function startPolling() {
    stopPolling()
    pollRef.current = setInterval(() => {
      const player = playerRef.current
      if (!player || !readyRef.current) return
      tick(Math.floor(player.getCurrentTime() * 1000))
    }, 200)
  }

  function stopPolling() {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  return (
    <div className="border-b border-zinc-800 bg-zinc-950 px-6 py-4">
      <div className="mx-auto max-w-3xl">
        <div className="overflow-hidden rounded-xl shadow-2xl">
          <div ref={containerRef} className="aspect-video w-full" />
        </div>
      </div>
    </div>
  )
}
