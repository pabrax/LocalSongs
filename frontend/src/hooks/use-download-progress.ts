"use client"

import { useState, useCallback, useRef, useEffect } from "react"
import type { DownloadRequest, DownloadWithProgressResponse, ProgressData } from "@/src/types/api"

export interface UseDownloadProgressResult {
  isLoading: boolean
  progress: number
  status: string
  message: string
  error: string | null
  downloadId: string | null
  startDownload: (url: string, quality?: string) => Promise<boolean>
  cancelDownload: () => void
  clearError: () => void
}

export function useDownloadProgress(): UseDownloadProgressResult {
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState("idle")
  const [message, setMessage] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [downloadId, setDownloadId] = useState<string | null>(null)
  
  const eventSourceRef = useRef<EventSource | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const cancelDownload = useCallback(() => {
    // Cerrar EventSource si existe
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    
    // Cancelar request si existe
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    
    // Limpiar estado
    setIsLoading(false)
    setProgress(0)
    setStatus("cancelled")
    setMessage("Descarga cancelada")
    setDownloadId(null)
  }, [])

  const startDownload = useCallback(async (url: string, quality = "192"): Promise<boolean> => {
    try {
      setError(null)
      setIsLoading(true)
      setProgress(0)
      setStatus("starting")
      setMessage("Iniciando descarga...")

      // Crear AbortController para cancelación
      abortControllerRef.current = new AbortController()

      const downloadRequest: DownloadRequest = {
        url,
        quality,
        output_format: "mp3"
      }

      // Iniciar descarga con progreso
      const response = await fetch("/api/download-with-progress", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(downloadRequest),
        signal: abortControllerRef.current.signal,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || "Error al iniciar la descarga")
      }

      const downloadResponse: DownloadWithProgressResponse = await response.json()
      setDownloadId(downloadResponse.download_id)
      setMessage(downloadResponse.message)

      // Conectar a Server-Sent Events para progreso
      const eventSource = new EventSource(`/api/progress-stream/${downloadResponse.download_id}`)
      eventSourceRef.current = eventSource

      eventSource.onmessage = (event) => {
        try {
          const progressData: ProgressData = JSON.parse(event.data)
          
          setProgress(progressData.progress)
          setStatus(progressData.status)
          setMessage(progressData.message)
          
          if (progressData.error) {
            setError(progressData.error)
          }
          
          // Si la descarga está completa o falló, cerrar conexión
          if (progressData.status === 'completed' || 
              progressData.status === 'success' || 
              progressData.status === 'error' || 
              progressData.status === 'failed' ||
              progressData.status === 'stream_ended') {
            eventSource.close()
            eventSourceRef.current = null
            setIsLoading(false)
            
            // Si es exitoso, descargar el archivo
            if (progressData.status === 'completed' || progressData.status === 'success') {
              // Trigger file download usando el nombre real del archivo
              setTimeout(async () => {
                try {
                  const filename = progressData.filename || `audio_${quality}kbps.mp3`
                  const fileResponse = await fetch(`/api/download-file/${encodeURIComponent(filename)}`)
                  if (fileResponse.ok) {
                    const blob = await fileResponse.blob()
                    const downloadUrl = window.URL.createObjectURL(blob)
                    const a = document.createElement("a")
                    a.href = downloadUrl
                    a.download = filename
                    document.body.appendChild(a)
                    a.click()
                    window.URL.revokeObjectURL(downloadUrl)
                    document.body.removeChild(a)
                  } else {
                    console.error("Error downloading file:", fileResponse.status)
                  }
                } catch (e) {
                  console.error("Error downloading file:", e)
                }
              }, 1000)
            }
          }
        } catch (e) {
          console.error("Error parsing progress data:", e)
          setError("Error procesando datos de progreso")
        }
      }

      eventSource.onerror = (event) => {
        console.error("EventSource error:", event)
        setError("Error en la conexión de progreso")
        eventSource.close()
        eventSourceRef.current = null
        setIsLoading(false)
      }

      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Error desconocido al descargar"
      setError(errorMessage)
      setIsLoading(false)
      setStatus("error")
      setMessage("Error en la descarga")
      return false
    }
  }, [])

  // Cleanup al desmontar el componente
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  return {
    isLoading,
    progress,
    status,
    message,
    error,
    downloadId,
    startDownload,
    cancelDownload,
    clearError
  }
}
