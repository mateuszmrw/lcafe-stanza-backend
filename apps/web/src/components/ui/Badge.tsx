import { cn } from "@/src/lib/cn"

type Variant = "zinc" | "blue" | "green" | "red" | "yellow"

const variants: Record<Variant, string> = {
  zinc: "bg-zinc-700 text-zinc-300",
  blue: "bg-blue-900/50 text-blue-300",
  green: "bg-green-900/50 text-green-300",
  red: "bg-red-900/50 text-red-300",
  yellow: "bg-yellow-900/50 text-yellow-300",
}

export function Badge({
  children,
  variant = "zinc",
  className,
}: {
  children: React.ReactNode
  variant?: Variant
  className?: string
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  )
}
