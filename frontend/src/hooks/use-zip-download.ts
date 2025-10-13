import { useState, useCallback } from 'react'
import { ZipDownloadResponse } from '@/types/api'

interface UseZipDownloadReturn {
  isCreatingZip: boolean
  zipError: string | null
  createZip: (downloadId: string) => Promise<ZipDownloadResponse>
  downloadZip: (zipFile: string) => void
  cleanupFiles: (downloadId: string, keepZip?: boolean) => Promise<boolean>
  moveFilesExternal: (downloadId: string, externalDir: string) => Promise<boolean>
  clearError: () => void
}

export function useZipDownload(): UseZipDownloadReturn {
  const [isCreatingZip, setIsCreatingZip] = useState(false)
  const [zipError, setZipError] = useState<string | null>(null)

  const createZip = useCallback(async (downloadId: string): Promise<ZipDownloadResponse> => {
    setIsCreatingZip(true)
    setZipError(null)

    try {
      const response = await fetch(`/api/create-zip/${downloadId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      const result: ZipDownloadResponse = await response.json()

      if (!response.ok) {
        throw new Error(result.error || 'Error creating ZIP file')
      }

      if (!result.success) {
        throw new Error(result.error || 'Failed to create ZIP file')
      }

      return result
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      setZipError(errorMessage)
      throw error
    } finally {
      setIsCreatingZip(false)
    }
  }, [])

  const downloadZip = useCallback((zipFile: string) => {
    try {
      const filename = zipFile.split('/').pop() || 'playlist.zip'
      const downloadUrl = `/api/download-file/${filename}`
      
      // Create a temporary link and trigger download
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (error) {
      console.error('Error triggering download:', error)
      setZipError('Error downloading ZIP file')
    }
  }, [])

  const cleanupFiles = useCallback(async (downloadId: string, keepZip: boolean = true): Promise<boolean> => {
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

      return result.success
    } catch (error) {
      console.error('Error cleaning up files:', error)
      setZipError(error instanceof Error ? error.message : 'Error cleaning up files')
      return false
    }
  }, [])

  const moveFilesExternal = useCallback(async (downloadId: string, externalDir: string): Promise<boolean> => {
    try {
      const response = await fetch(`/api/move-external/${downloadId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ external_dir: externalDir }),
      })

      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.error || 'Error moving files')
      }

      return result.success
    } catch (error) {
      console.error('Error moving files:', error)
      setZipError(error instanceof Error ? error.message : 'Error moving files')
      return false
    }
  }, [])

  const clearError = useCallback(() => {
    setZipError(null)
  }, [])

  return {
    isCreatingZip,
    zipError,
    createZip,
    downloadZip,
    cleanupFiles,
    moveFilesExternal,
    clearError
  }
}