"use client"

import { useState, useCallback } from "react"
import type { DownloadRequest, DownloadResponse, AudioInfoResponse } from "@/src/types/api"

export interface UseDownloadResult {
  isLoading: boolean
  error: string | null
  downloadFile: (url: string, quality?: string) => Promise<boolean>
  getAudioInfo: (url: string) => Promise<AudioInfoResponse | null>
  clearError: () => void
}

export function useDownload(): UseDownloadResult {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const getAudioInfo = useCallback(async (url: string): Promise<AudioInfoResponse | null> => {
    try {
      setError(null)
      const response = await fetch(`/api/info?url=${encodeURIComponent(url)}`)
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || "Error al obtener información")
      }

      return await response.json()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Error desconocido"
      setError(errorMessage)
      return null
    }
  }, [])

  const downloadFile = useCallback(async (url: string, quality = "192"): Promise<boolean> => {
    setIsLoading(true)
    setError(null)

    try {
      const downloadRequest: DownloadRequest = {
        url,
        quality,
        output_format: "mp3"
      }

      const response = await fetch("/api/download", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(downloadRequest),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || "Error al descargar el archivo")
      }

      // Obtener información del archivo
      const contentDisposition = response.headers.get("Content-Disposition")
      const fileNameMatch = contentDisposition?.match(/filename="?(.+)"?/)
      const fileName = fileNameMatch ? fileNameMatch[1] : "audio.mp3"

      // Crear y descargar el archivo
      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = downloadUrl
      a.download = fileName
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(downloadUrl)
      document.body.removeChild(a)

      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Error desconocido al descargar"
      setError(errorMessage)
      return false
    } finally {
      setIsLoading(false)
    }
  }, [])

  return {
    isLoading,
    error,
    downloadFile,
    getAudioInfo,
    clearError
  }
}