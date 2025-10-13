"use client"

import React from "react"
import { cn } from "@/src/lib/utils"
import type { MultiProgressData, FileInfo } from "@/src/types/api"
import { ProgressBar } from "./progress-bar"

interface MultiProgressBarProps {
  multiProgress: MultiProgressData
  className?: string
  showFileList?: boolean
  maxVisibleFiles?: number
}

export function MultiProgressBar({
  multiProgress,
  className,
  showFileList = true,
  maxVisibleFiles = 5
}: MultiProgressBarProps) {
  const getOverallStatusColor = () => {
    switch (multiProgress.overall_status) {
      case "completed":
      case "success":
        return "text-green-600"
      case "error":
      case "failed":
        return "text-red-600"
      case "downloading":
        return "text-blue-600"
      default:
        return "text-gray-600"
    }
  }

  const getOverallStatusIcon = () => {
    switch (multiProgress.overall_status) {
      case "completed":
      case "success":
        return "🎉"
      case "error":
      case "failed":
        return "❌"
      case "downloading":
        return "📥"
      case "starting":
        return "⚙️"
      default:
        return "📋"
    }
  }

  const getFileStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return "✅"
      case "failed":
        return "❌"
      case "downloading":
        return "⬇️"
      case "pending":
        return "⏳"
      default:
        return "📄"
    }
  }

  const visibleFiles = showFileList 
    ? multiProgress.files_info.slice(0, maxVisibleFiles)
    : []
  
  const hasMoreFiles = multiProgress.files_info.length > maxVisibleFiles

  return (
    <div className={cn("w-full space-y-4", className)}>
      {/* Overall Progress */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">{getOverallStatusIcon()}</span>
            <span className="font-semibold">
              Playlist Progress ({multiProgress.completed_files}/{multiProgress.total_files})
            </span>
          </div>
          <span className={cn("font-bold text-sm", getOverallStatusColor())}>
            {multiProgress.overall_progress}%
          </span>
        </div>

        {/* Overall progress bar */}
        <ProgressBar
          value={multiProgress.overall_progress}
          status={multiProgress.overall_status}
          message={multiProgress.message}
          showPercentage={false}
          animated={multiProgress.overall_status === "downloading"}
        />

        {/* Stats */}
        <div className="flex gap-4 text-xs text-muted-foreground">
          <span>✅ Completados: {multiProgress.completed_files}</span>
          {multiProgress.failed_files > 0 && (
            <span>❌ Fallidos: {multiProgress.failed_files}</span>
          )}
          <span>⏳ Pendientes: {multiProgress.total_files - multiProgress.completed_files - multiProgress.failed_files}</span>
        </div>
      </div>

      {/* Current File Progress */}
      {multiProgress.overall_status === "downloading" && multiProgress.current_file_name && (
        <div className="p-3 bg-muted/20 rounded-lg border">
          <div className="text-sm font-medium mb-2">
            Archivo Actual: {multiProgress.current_file_name}
          </div>
          <ProgressBar
            value={multiProgress.current_file_progress}
            status={multiProgress.current_file_status}
            showPercentage={true}
            animated={true}
            className="h-2"
          />
        </div>
      )}

      {/* File List */}
      {showFileList && visibleFiles.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">
            Archivos ({multiProgress.files_info.length} total)
          </h4>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {visibleFiles.map((file: FileInfo) => (
              <div
                key={file.index}
                className={cn(
                  "flex items-center gap-2 p-2 rounded text-xs",
                  file.status === "completed" && "bg-green-50 border border-green-200",
                  file.status === "failed" && "bg-red-50 border border-red-200",
                  file.status === "downloading" && "bg-blue-50 border border-blue-200",
                  file.status === "pending" && "bg-gray-50 border border-gray-200"
                )}
              >
                <span className="text-base">{getFileStatusIcon(file.status)}</span>
                <div className="flex-1 min-w-0">
                  <div className="truncate font-medium">
                    {file.name || `Archivo ${file.index + 1}`}
                  </div>
                  {file.error && (
                    <div className="text-red-600 text-xs truncate">
                      Error: {file.error}
                    </div>
                  )}
                  {file.message && file.status === "downloading" && (
                    <div className="text-blue-600 text-xs truncate">
                      {file.message}
                    </div>
                  )}
                </div>
                {file.status === "downloading" && (
                  <div className="text-xs font-mono">
                    {file.progress}%
                  </div>
                )}
              </div>
            ))}
          </div>
          
          {hasMoreFiles && (
            <div className="text-xs text-muted-foreground text-center py-2">
              ... y {multiProgress.files_info.length - maxVisibleFiles} archivos más
            </div>
          )}
        </div>
      )}

      {/* Error Display */}
      {multiProgress.error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <div className="text-sm text-red-800">
            <strong>Error:</strong> {multiProgress.error}
          </div>
        </div>
      )}
    </div>
  )
}
