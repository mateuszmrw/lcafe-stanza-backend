import { z } from "zod"

export const youtubeUrlSchema = z.object({
  url: z.url({ error: "Please enter a valid URL" }),
})

export const websiteUrlSchema = z.object({
  url: z.url({ error: "Please enter a valid URL" }),
})
