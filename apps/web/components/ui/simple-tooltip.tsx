"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

// Simple CSS-only tooltip that doesn't require React context
// This avoids SSR issues with Radix UI TooltipProvider

export function SimpleTooltip({
  children,
  content,
  side = "top",
  className,
}: {
  children: React.ReactNode
  content: React.ReactNode
  side?: "top" | "bottom" | "left" | "right"
  className?: string
}) {
  return (
    <div className="relative inline-block group">
      {children}
      <div
        className={cn(
          "pointer-events-none absolute z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-150",
          "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-xs rounded-md px-3 py-1.5 whitespace-nowrap",
          side === "top" && "bottom-full left-1/2 -translate-x-1/2 mb-2",
          side === "bottom" && "top-full left-1/2 -translate-x-1/2 mt-2",
          side === "left" && "right-full top-1/2 -translate-y-1/2 mr-2",
          side === "right" && "left-full top-1/2 -translate-y-1/2 ml-2",
          className
        )}
      >
        {content}
      </div>
    </div>
  )
}
