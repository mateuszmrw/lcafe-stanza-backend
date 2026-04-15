"use client"

import { useMemo } from "react"
import {
  type SentenceToken,
  getDepCategory,
  ARC_STROKE_COLORS,
} from "@/src/lib/grammar"

interface DependencyArcsProps {
  tokens: SentenceToken[]
}

const TOKEN_WIDTH = 70
const TOKEN_GAP = 8
const LABEL_HEIGHT = 22
const ARC_BASE_Y = 10
const ARC_HEIGHT_PER_SPAN = 18

export function DependencyArcs({ tokens }: DependencyArcsProps) {
  // Filter out punctuation for the diagram
  const wordTokens = useMemo(
    () => tokens.filter((t) => t.pos !== "PUNCT"),
    [tokens]
  )

  // Build position map: original 1-based index → diagram position
  const posMap = useMemo(() => {
    const map = new Map<number, number>()
    let pos = 0
    tokens.forEach((t, i) => {
      if (t.pos !== "PUNCT") {
        map.set(i + 1, pos) // tokens are 1-based in dep_head
        pos++
      }
    })
    return map
  }, [tokens])

  const totalWidth = wordTokens.length * (TOKEN_WIDTH + TOKEN_GAP)

  // Calculate arcs
  const arcs = useMemo(() => {
    return wordTokens
      .map((t, diagIdx) => {
        if (t.dep_head === 0 || t.dep_rel === "punct") return null
        const headDiagIdx = posMap.get(t.dep_head)
        if (headDiagIdx === undefined) return null
        const span = Math.abs(diagIdx - headDiagIdx)
        if (span === 0) return null
        return {
          from: diagIdx,
          to: headDiagIdx,
          label: t.dep_rel,
          cat: getDepCategory(t.dep_rel),
          span,
        }
      })
      .filter(Boolean) as Array<{
        from: number; to: number; label: string; cat: string; span: number
      }>
  }, [wordTokens, posMap])

  const maxSpan = Math.max(1, ...arcs.map((a) => a.span))
  const arcAreaHeight = maxSpan * ARC_HEIGHT_PER_SPAN + 20
  const svgHeight = arcAreaHeight + LABEL_HEIGHT + 30

  return (
    <div className="overflow-x-auto">
      <svg
        width={totalWidth}
        height={svgHeight}
        className="block"
        style={{ minWidth: totalWidth }}
      >
        {/* Arcs */}
        {arcs.map((arc, i) => {
          const fromX = arc.from * (TOKEN_WIDTH + TOKEN_GAP) + TOKEN_WIDTH / 2
          const toX = arc.to * (TOKEN_WIDTH + TOKEN_GAP) + TOKEN_WIDTH / 2
          const midX = (fromX + toX) / 2
          const height = arc.span * ARC_HEIGHT_PER_SPAN + 10
          const y = arcAreaHeight - ARC_BASE_Y
          const strokeColor = ARC_STROKE_COLORS[arc.cat as keyof typeof ARC_STROKE_COLORS] ?? "#71717a"

          return (
            <g key={i}>
              <path
                d={`M ${fromX} ${y} Q ${midX} ${y - height} ${toX} ${y}`}
                fill="none"
                stroke={strokeColor}
                strokeWidth={1.5}
                opacity={0.7}
              />
              {/* Arc label */}
              <text
                x={midX}
                y={y - height + 4}
                textAnchor="middle"
                className="fill-zinc-500"
                fontSize={9}
              >
                {arc.label}
              </text>
              {/* Arrow head on the dependent side */}
              <circle cx={fromX} cy={y} r={2.5} fill={strokeColor} opacity={0.8} />
            </g>
          )
        })}

        {/* Token labels */}
        {wordTokens.map((t, i) => {
          const x = i * (TOKEN_WIDTH + TOKEN_GAP) + TOKEN_WIDTH / 2
          const y = arcAreaHeight + 6
          const cat = getDepCategory(t.dep_rel)
          const fillColor = ARC_STROKE_COLORS[cat as keyof typeof ARC_STROKE_COLORS] ?? "#a1a1aa"

          return (
            <g key={i}>
              <text
                x={x}
                y={y}
                textAnchor="middle"
                fill={fillColor}
                fontSize={13}
                fontWeight={600}
              >
                {t.w}
              </text>
              <text
                x={x}
                y={y + 14}
                textAnchor="middle"
                className="fill-zinc-600"
                fontSize={9}
              >
                {t.pos}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
