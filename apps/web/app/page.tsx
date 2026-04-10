"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { getSetupStatus } from "@/src/lib/api/auth"

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    getSetupStatus()
      .then(({ needs_setup }) => {
        router.replace(needs_setup ? "/setup" : "/library")
      })
      .catch(() => {
        router.replace("/library")
      })
  }, [router])

  return null
}
