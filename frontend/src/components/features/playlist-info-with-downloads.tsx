"use client"

import React from "react"
import { cn } from "@/src/lib/utils"
import type { PlaylistInfo, DownloadedFile } from "@/src/types/api"
import { Badge } from "../ui/badge"
import { Card } from "../ui/card"
import { Button } from "../ui/button"
import { Download, CheckCircle2, Loader2, Archive, Trash2 } from "lucide-react"

interface PlaylistInfoWithDownloadsProps {
  playlistInfo: PlaylistInfo
  downloadedFiles?: DownloadedFile[]
  isLoadingFiles?: boolean
  onDownloadFile?: (fileName: string) => Promise<boolean>
  onRefreshFiles?: () => Promise<void>
  
  // ZIP functionality
  isCreatingZip?: boolean
  zipFile?: string | null
  onCreateZip?: () => Promise<boolean>
  onDownloadZip?: () => void
  onCleanupFiles?: (keepZip?: boolean) => Promise<boolean>
  
  className?: string
  showTrackList?: boolean
  maxVisibleTracks?: number
  showZipControls?: boolean
}

export function PlaylistInfoWithDownloads({
  playlistInfo,
  downloadedFiles = [],
  isLoadingFiles = false,
  onDownloadFile,
  onRefreshFiles,
  
  // ZIP props
  isCreatingZip = false,
  zipFile = null,
  onCreateZip,
  onDownloadZip,
  onCleanupFiles,
  
  className,
  showTrackList = true,
  maxVisibleTracks = 10,
  showZipControls = false
}: PlaylistInfoWithDownloadsProps) {
  // Verificación defensiva para prevenir errores de undefined
  if (!playlistInfo) {
    return null
  }
  
  // Asegurar que las propiedades críticas existan
  const safePlaylistInfo = {
    ...playlistInfo,
    tracks: playlistInfo.tracks || [],
    type: playlistInfo.type || 'unknown',
    platform: playlistInfo.platform || 'unknown',
    title: playlistInfo.title || 'Unknown Title',
    total_tracks: playlistInfo.total_tracks || 0
  }
  
  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case "spotify":
        return "🎵"
      case "youtube":
        return "📺"
      case "youtube_music":
        return "🎶"
      default:
        return "🎧"
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "album":
        return "💿"
      case "playlist":
        return "📋"
      case "track":
        return "🎵"
      default:
        return "🎧"
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case "album":
        return "bg-purple-500/20 text-purple-400 border-purple-500/30"
      case "playlist":
        return "bg-blue-500/20 text-blue-400 border-blue-500/30"
      case "track":
        return "bg-green-500/20 text-green-400 border-green-500/30"
      default:
        return "bg-gray-500/20 text-gray-400 border-gray-500/30"
    }
  }

  // Verificar si un track está descargado
  const isTrackDownloaded = (trackName: string) => {
    return downloadedFiles.some(file => 
      file.name.toLowerCase().includes(trackName.toLowerCase().split(' - ')[1]?.toLowerCase() || trackName.toLowerCase())
    )
  }

  // Obtener archivo descargado para un track
  const getDownloadedFile = (trackName: string) => {
    return downloadedFiles.find(file => 
      file.name.toLowerCase().includes(trackName.toLowerCase().split(' - ')[1]?.toLowerCase() || trackName.toLowerCase())
    )
  }

  const visibleTracks = showTrackList && safePlaylistInfo.tracks
    ? safePlaylistInfo.tracks.slice(0, maxVisibleTracks)
    : []
  
  const hasMoreTracks = safePlaylistInfo.tracks ? safePlaylistInfo.tracks.length > maxVisibleTracks : false
  const downloadedCount = downloadedFiles.length

  return (
    <Card className={cn("p-6 space-y-6 bg-gradient-to-br from-slate-900/50 to-slate-800/50 border-slate-700/50", className)}>
      {/* Header */}
      <div className="space-y-3">
        <div className="flex items-start gap-4">
          <div className="text-3xl">
            {getTypeIcon(safePlaylistInfo.type)}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-xl text-slate-100 truncate">
              {safePlaylistInfo.title}
            </h3>
            {safePlaylistInfo.uploader && (
              <p className="text-sm text-slate-400 truncate mt-1">
                por {safePlaylistInfo.uploader}
              </p>
            )}
          </div>
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-2">
          <Badge className={getTypeColor(safePlaylistInfo.type)}>
            {getTypeIcon(safePlaylistInfo.type)} {safePlaylistInfo.type?.charAt(0).toUpperCase() + safePlaylistInfo.type?.slice(1)}
          </Badge>
          
          <Badge variant="outline" className="bg-slate-800/50 text-slate-300 border-slate-600">
            {getPlatformIcon(safePlaylistInfo.platform)} {safePlaylistInfo.platform.replace('_', ' ').toUpperCase()}
          </Badge>
          
          <Badge variant="outline" className="bg-slate-800/50 text-slate-300 border-slate-600">
            📊 {safePlaylistInfo.total_tracks} {safePlaylistInfo.total_tracks === 1 ? 'track' : 'tracks'}
          </Badge>

          {downloadedCount > 0 && (
            <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
              ✅ {downloadedCount} descargados
            </Badge>
          )}

          {playlistInfo.limited && (
            <Badge variant="destructive" className="bg-red-500/20 text-red-400 border-red-500/30">
              ⚠️ Limitado a 50 tracks
            </Badge>
          )}
        </div>
      </div>

      {/* Track List with Download Status */}
      {showTrackList && visibleTracks.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-slate-300">
              Tracks {downloadedCount > 0 ? `(${downloadedCount}/${playlistInfo.total_tracks} descargados)` : ''}:
            </h4>
            {onRefreshFiles && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRefreshFiles}
                disabled={isLoadingFiles}
                className="bg-slate-800/50 border-slate-600 text-slate-300 hover:bg-slate-700/50"
              >
                {isLoadingFiles ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  "🔄"
                )}
              </Button>
            )}
          </div>
          
          <div className="space-y-2 max-h-64 overflow-y-auto scrollbar-thin scrollbar-track-slate-800 scrollbar-thumb-slate-600">
            {visibleTracks.map((track, index) => {
              const isDownloaded = isTrackDownloaded(track)
              const downloadedFile = getDownloadedFile(track)
              
              return (
                <div
                  key={index}
                  className={cn(
                    "flex items-center gap-3 p-3 rounded-lg border transition-colors",
                    isDownloaded 
                      ? "bg-green-500/10 border-green-500/30" 
                      : "bg-slate-800/30 border-slate-700/50 hover:bg-slate-700/30"
                  )}
                >
                  <span className="text-xs text-slate-500 font-mono w-8">
                    {(index + 1).toString().padStart(2, '0')}
                  </span>
                  
                  <div className="flex-1 min-w-0">
                    <span className={cn(
                      "text-sm truncate block",
                      isDownloaded ? "text-green-400" : "text-slate-300"
                    )}>
                      {track}
                    </span>
                    {downloadedFile && (
                      <span className="text-xs text-slate-500">
                        {(downloadedFile.size / 1024 / 1024).toFixed(1)} MB
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {isDownloaded ? (
                      <>
                        <CheckCircle2 className="w-5 h-5 text-green-400" />
                        {onDownloadFile && downloadedFile && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onDownloadFile(downloadedFile.name)}
                            className="bg-slate-800/50 border-slate-600 text-slate-300 hover:bg-slate-700/50 px-2 py-1 h-7"
                          >
                            <Download className="w-3 h-3" />
                          </Button>
                        )}
                      </>
                    ) : (
                      <div className="w-5 h-5 rounded-full border-2 border-slate-600" />
                    )}
                  </div>
                </div>
              )
            })}
          </div>
          
          {hasMoreTracks && safePlaylistInfo.tracks && (
            <div className="text-xs text-slate-500 text-center py-2 border-t border-slate-700">
              ... y {safePlaylistInfo.tracks.length - maxVisibleTracks} tracks más
            </div>
          )}
        </div>
      )}

      {/* Warning for large playlists */}
      {playlistInfo.total_tracks > 20 && (
        <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
          <div className="text-sm text-yellow-400">
            <strong>⚠️ Playlist grande:</strong> Esta descarga puede tomar varios minutos. 
            {playlistInfo.limited && " Se descargarán solo los primeros 50 tracks por seguridad."}
          </div>
        </div>
      )}

      {/* Platform-specific info */}
      {playlistInfo.platform === "spotify" && (
        <div className="text-xs text-slate-500 bg-slate-800/30 p-2 rounded">
          💡 Los tracks de Spotify se buscarán automáticamente en YouTube para la descarga
        </div>
      )}

      {/* ZIP Controls */}
      {showZipControls && (
        <div className="mt-4 p-4 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-teal-500/10 border border-blue-500/20 rounded-lg">
          <h4 className="text-sm font-semibold text-blue-400 mb-3 flex items-center gap-2">
            <Archive className="w-4 h-4" />
            Descargar como ZIP
          </h4>
          
          <div className="space-y-3">
            <p className="text-xs text-slate-400">
              Descarga todos los archivos de la playlist en un archivo ZIP comprimido.
            </p>
            
            <div className="flex flex-col xs:flex-row gap-2">
              {!zipFile ? (
                <Button
                  onClick={onCreateZip}
                  disabled={isCreatingZip || !onCreateZip}
                  size="sm"
                  className="h-9 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white text-xs"
                >
                  {isCreatingZip ? (
                    <>
                      <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                      Creando ZIP...
                    </>
                  ) : (
                    <>
                      <Archive className="w-3 h-3 mr-1" />
                      Crear ZIP
                    </>
                  )}
                </Button>
              ) : (
                <>
                  <Button
                    onClick={onDownloadZip}
                    disabled={!onDownloadZip}
                    size="sm"
                    className="h-9 bg-gradient-to-r from-green-600 to-teal-600 hover:from-green-700 hover:to-teal-700 text-white text-xs"
                  >
                    <Download className="w-3 h-3 mr-1" />
                    Descargar ZIP
                  </Button>
                  
                  <Button
                    onClick={() => onCleanupFiles?.(true)}
                    variant="outline"
                    size="sm"
                    className="h-9 border-orange-500/20 text-orange-400 hover:bg-orange-500/10 text-xs"
                  >
                    <Trash2 className="w-3 h-3 mr-1" />
                    Limpiar
                  </Button>
                </>
              )}
            </div>
            
            {zipFile && (
              <p className="text-xs text-green-400 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                ZIP listo: {zipFile.split('/').pop()}
              </p>
            )}
          </div>
        </div>
      )}
    </Card>
  )
}