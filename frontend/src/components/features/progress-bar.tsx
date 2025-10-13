"use client"

import React from "react"
import { cn } from "@/src/lib/utils"

interface ProgressBarProps {
  value: number
  max?: number
  className?: string
  showPercentage?: boolean
  status?: string
  message?: string
  animated?: boolean
}

export function ProgressBar({
  value,
  max = 100,
  className,
  showPercentage = true,
  status = "progress",
  message,
  animated = true
}: ProgressBarProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)
  
  const getStatusColor = () => {
    switch (status) {
      case "completed":
      case "success":
        return "bg-green-500"
      case "error":
      case "failed":
        return "bg-red-500"
      case "downloading":
        return "bg-blue-500"
      case "converting":
        return "bg-yellow-500"
      case "preparing":
        return "bg-purple-500"
      case "finalizing":
        return "bg-indigo-500"
      default:
        return "bg-primary"
    }
  }

  const getStatusIcon = () => {
    switch (status) {
      case "completed":
      case "success":
        return "✅"
      case "error":
      case "failed":
        return "❌"
      case "downloading":
        return "⬇️"
      case "converting":
        return "🔄"
      case "preparing":
        return "⚙️"
      case "finalizing":
        return "✨"
      default:
        return "📥"
    }
  }

  return (
    <div className={cn("w-full space-y-2", className)}>
      {/* Progress info */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <span className="text-lg">{getStatusIcon()}</span>
          <span className="font-medium capitalize">{status.replace('_', ' ')}</span>
        </div>
        {showPercentage && (
          <span className="font-mono font-bold">
            {Math.round(percentage)}%
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div className="relative h-3 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn(
            "h-full transition-all duration-300 ease-out",
            getStatusColor(),
            animated && percentage > 0 && "animate-pulse"
          )}
          style={{
            width: `${percentage}%`,
            transition: animated ? "width 0.3s ease-out" : "none"
          }}
        />
        
        {/* Shimmer effect for active downloads */}
        {animated && status === "downloading" && percentage > 0 && percentage < 100 && (
          <div
            className="absolute top-0 h-full w-8 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer"
            style={{
              left: `${Math.max(0, percentage - 10)}%`,
              animation: "shimmer 2s infinite"
            }}
          />
        )}
      </div>

      {/* Message */}
      {message && (
        <div className="text-xs text-muted-foreground">
          {message}
        </div>
      )}

      <style jsx>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        .animate-shimmer {
          animation: shimmer 2s infinite;
        }
      `}</style>
    </div>
  )
}
