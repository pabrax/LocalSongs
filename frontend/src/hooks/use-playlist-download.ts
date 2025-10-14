"use client"

import { useState, useCallback, useRef, useEffect } from "react"
import type { 
  DownloadRequest, 
  PlaylistDownloadResponse, 
  MultiProgressData, 
  PlaylistInfo,
  PlaylistInfoResponse,
  DownloadedFile,
  ListFilesResponse
} from "@/src/types/api"

export interface UsePlaylistDownloadResult {
  // Playlist info
  playlistInfo: PlaylistInfo | null
  isLoadingInfo: boolean
  
  // Download progress
  isDownloading: boolean
  multiProgress: MultiProgressData | null
  
  // Downloaded files
  downloadedFiles: DownloadedFile[]
  isLoadingFiles: boolean
  
  // ZIP functionality
  isCreatingZip: boolean
  zipFile: string | null
  
  // States
  error: string | null
  downloadId: string | null
  
  // Actions
  getPlaylistInfo: (url: string) => Promise<boolean>
  startPlaylistDownload: (url: string, quality?: string) => Promise<boolean>
  cancelDownload: () => void
  clearError: () => void
  refreshDownloadedFiles: () => Promise<void>
  downloadFile: (fileName: string) => Promise<boolean>
  
  // ZIP actions
  createZip: () => Promise<boolean>
  downloadZip: () => void
  cleanupFiles: (keepZip?: boolean) => Promise<boolean>
}

export function usePlaylistDownload(): UsePlaylistDownloadResult {
  const [playlistInfo, setPlaylistInfo] = useState<PlaylistInfo | null>(null)
  const [isLoadingInfo, setIsLoadingInfo] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const [multiProgress, setMultiProgress] = useState<MultiProgressData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [downloadId, setDownloadId] = useState<string | null>(null)
  const [downloadedFiles, setDownloadedFiles] = useState<DownloadedFile[]>([])
  const [isLoadingFiles, setIsLoadingFiles] = useState(false)
  
  // ZIP states
  const [isCreatingZip, setIsCreatingZip] = useState(false)
  const [zipFile, setZipFile] = useState<string | null>(null)
  
  const eventSourceRef = useRef<EventSource | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const refreshDownloadedFiles = useCallback(async () => {
    if (!playlistInfo?.title) return
    
    try {
      setIsLoadingFiles(true)
      setError(null)
      
      // Crear nombre de carpeta similar al backend
      const folderName = `${playlistInfo.title} [${playlistInfo.type}] [${playlistInfo.platform}]`
      
      const response = await fetch(`/api/list-files?folder=${encodeURIComponent(folderName)}`)
      
      if (!response.ok) {
        throw new Error("Error loading downloaded files")
      }
      
      const result: ListFilesResponse = await response.json()
      
      if (result.success) {
        setDownloadedFiles(result.files)
      } else {
        setDownloadedFiles([])
      }
    } catch (err) {
      console.error("Error refreshing downloaded files:", err)
      setDownloadedFiles([])
    } finally {
      setIsLoadingFiles(false)
    }
  }, [playlistInfo])

  const downloadFile = useCallback(async (fileName: string): Promise<boolean> => {
    try {
      setError(null)
      
      const response = await fetch(`/api/download-file/${encodeURIComponent(fileName)}`)
      
      if (!response.ok) {
        throw new Error("Error downloading file")
      }
      
      // Crear blob y descargar
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fileName
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Error downloading file"
      setError(errorMessage)
      return false
    }
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
    setIsDownloading(false)
    setMultiProgress(null)
    setDownloadId(null)
  }, [])

  const getPlaylistInfo = useCallback(async (url: string): Promise<boolean> => {
    try {
      setError(null)
      setIsLoadingInfo(true)
      setPlaylistInfo(null)

      const response = await fetch(`/api/playlist-info?url=${encodeURIComponent(url)}`, {
        method: "GET",
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || "Error al obtener información del playlist")
      }

      const result: PlaylistInfoResponse = await response.json()
      
      if (result.success && result.info) {
        setPlaylistInfo(result.info)
        return true
      } else {
        throw new Error("No se pudo obtener información del playlist")
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Error desconocido"
      setError(errorMessage)
      return false
    } finally {
      setIsLoadingInfo(false)
    }
  }, [])

  const startPlaylistDownload = useCallback(async (url: string, quality = "192"): Promise<boolean> => {
    try {
      setError(null)
      setIsDownloading(true)
      setMultiProgress(null)

      // Crear AbortController para cancelación
      abortControllerRef.current = new AbortController()

      const downloadRequest: DownloadRequest = {
        url,
        quality,
        output_format: "mp3"
      }

      // Iniciar descarga de playlist
      const response = await fetch("/api/download-playlist", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(downloadRequest),
        signal: abortControllerRef.current.signal,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || "Error al iniciar la descarga del playlist")
      }

      const downloadResponse: PlaylistDownloadResponse = await response.json()
      setDownloadId(downloadResponse.download_id)
      
      // Actualizar info del playlist si no la tenemos
      if (!playlistInfo && downloadResponse.playlist_info) {
        setPlaylistInfo(downloadResponse.playlist_info)
      }

      // Conectar a Server-Sent Events para progreso multi-archivo
      const eventSource = new EventSource(`/api/multi-progress-stream/${downloadResponse.download_id}`)
      eventSourceRef.current = eventSource

      eventSource.onmessage = (event) => {
        try {
          const progressData: MultiProgressData = JSON.parse(event.data)
          
          setMultiProgress(progressData)
          
          if (progressData.error) {
            setError(progressData.error)
          }
          
          // Si la descarga está completa o falló, cerrar conexión
          if (progressData.overall_status === 'completed' || 
              progressData.overall_status === 'success' || 
              progressData.overall_status === 'error' || 
              progressData.overall_status === 'failed' ||
              progressData.overall_status === 'cancelled') {
            eventSource.close()
            eventSourceRef.current = null
            setIsDownloading(false)
            
            // Si es exitoso, mostrar mensaje de éxito y refrescar archivos
            if (progressData.overall_status === 'completed' || progressData.overall_status === 'success') {
              console.log(`Playlist descargado: ${progressData.completed_files}/${progressData.total_files} archivos`)
              // Establecer que el ZIP está listo para descarga
              if (downloadResponse.download_id) {
                setZipFile(`/api/v1/download-zip/${downloadResponse.download_id}`)
              }
              // Refrescar lista de archivos descargados
              setTimeout(() => {
                refreshDownloadedFiles()
              }, 1000)
            }
          }
        } catch (e) {
          console.error("Error parsing multi-progress data:", e)
          setError("Error procesando datos de progreso del playlist")
        }
      }

      eventSource.onerror = (event) => {
        console.error("EventSource error:", event)
        setError("Error en la conexión de progreso del playlist")
        eventSource.close()
        eventSourceRef.current = null
        setIsDownloading(false)
      }

      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Error desconocido al descargar playlist"
      setError(errorMessage)
      setIsDownloading(false)
      return false
    }
  }, [playlistInfo])

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

  // ZIP functions
  const createZip = useCallback(async (): Promise<boolean> => {
    if (!downloadId) {
      setError("No hay descarga activa para crear ZIP")
      return false
    }

    // El ZIP ya está disponible directamente desde el backend
    setZipFile(`/api/v1/download-zip/${downloadId}`)
    return true
  }, [downloadId])

  const downloadZip = useCallback(() => {
    if (!zipFile || !downloadId) {
      setError("No hay archivo ZIP disponible para descargar")
      return
    }

    try {
      // Usar el endpoint directo del backend
      const downloadUrl = `/api/v1/download-zip/${downloadId}`
      
      // Create a temporary link and trigger download
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = `playlist_${downloadId}.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (err) {
      console.error('Error triggering download:', err)
      setError('Error downloading ZIP file')
    }
  }, [zipFile, downloadId])

  const cleanupFiles = useCallback(async (keepZip: boolean = true): Promise<boolean> => {
    if (!downloadId) {
      setError("No hay descarga activa para limpiar")
      return false
    }

    try {
      const response = await fetch(`/api/cleanup/${downloadId}?keep_zip=${keepZip}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.error || 'Error cleaning up files')
      }

      // Refresh downloaded files list after cleanup
      await refreshDownloadedFiles()

      return result.success
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Error cleaning up files'
      setError(errorMessage)
      return false
    }
  }, [downloadId, refreshDownloadedFiles])

  return {
    playlistInfo,
    isLoadingInfo,
    isDownloading,
    multiProgress,
    downloadedFiles,
    isLoadingFiles,
    isCreatingZip,
    zipFile,
    error,
    downloadId,
    getPlaylistInfo,
    startPlaylistDownload,
    cancelDownload,
    clearError,
    refreshDownloadedFiles,
    downloadFile,
    createZip,
    downloadZip,
    cleanupFiles
  }
}
