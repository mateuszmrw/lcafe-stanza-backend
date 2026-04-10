import { z } from "zod"

const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z.url("NEXT_PUBLIC_API_URL must be a valid URL"),
})

const _parsed = envSchema.safeParse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
})

if (!_parsed.success) {
  const msgs = _parsed.error.issues
    .map((issue) => `  ${issue.path.join(".")}: ${issue.message}`)
    .join("\n")
  throw new Error(`Invalid environment variables:\n${msgs}`)
}

export const env = {
  apiUrl: _parsed.data.NEXT_PUBLIC_API_URL,
}
