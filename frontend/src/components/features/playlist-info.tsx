"use client"

import React from "react"
import { cn } from "@/src/lib/utils"
import type { PlaylistInfo } from "@/src/types/api"
import { Badge } from "@/src/components/ui/badge"
import { Card } from "@/src/components/ui/card"

interface PlaylistInfoProps {
  playlistInfo: PlaylistInfo
  className?: string
  showTrackList?: boolean
  maxVisibleTracks?: number
}

export function PlaylistInfoComponent({
  playlistInfo,
  className,
  showTrackList = true,
  maxVisibleTracks = 10
}: PlaylistInfoProps) {
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
        return "bg-purple-100 text-purple-800 border-purple-200"
      case "playlist":
        return "bg-blue-100 text-blue-800 border-blue-200"
      case "track":
        return "bg-green-100 text-green-800 border-green-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  const visibleTracks = showTrackList 
    ? playlistInfo.tracks.slice(0, maxVisibleTracks)
    : []
  
  const hasMoreTracks = playlistInfo.tracks.length > maxVisibleTracks

  return (
    <Card className={cn("p-4 space-y-4", className)}>
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-start gap-3">
          <div className="text-2xl">
            {getTypeIcon(playlistInfo.type)}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-lg truncate">
              {playlistInfo.title}
            </h3>
            {playlistInfo.uploader && (
              <p className="text-sm text-muted-foreground truncate">
                por {playlistInfo.uploader}
              </p>
            )}
          </div>
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-2">
          <Badge className={getTypeColor(playlistInfo.type)}>
            {getTypeIcon(playlistInfo.type)} {playlistInfo.type.charAt(0).toUpperCase() + playlistInfo.type.slice(1)}
          </Badge>
          
          <Badge variant="outline">
            {getPlatformIcon(playlistInfo.platform)} {playlistInfo.platform.replace('_', ' ').toUpperCase()}
          </Badge>
          
          <Badge variant="outline">
            📊 {playlistInfo.total_tracks} {playlistInfo.total_tracks === 1 ? 'track' : 'tracks'}
          </Badge>

          {playlistInfo.limited && (
            <Badge variant="destructive">
              ⚠️ Limitado a 50 tracks
            </Badge>
          )}
        </div>
      </div>

      {/* Track List */}
      {showTrackList && visibleTracks.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">
            Tracks a descargar:
          </h4>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {visibleTracks.map((track, index) => (
              <div
                key={index}
                className="flex items-center gap-2 p-2 rounded bg-muted/20 text-sm"
              >
                <span className="text-xs text-muted-foreground font-mono w-8">
                  {(index + 1).toString().padStart(2, '0')}
                </span>
                <span className="flex-1 truncate">
                  {track}
                </span>
              </div>
            ))}
          </div>
          
          {hasMoreTracks && (
            <div className="text-xs text-muted-foreground text-center py-2 border-t">
              ... y {playlistInfo.tracks.length - maxVisibleTracks} tracks más
            </div>
          )}
        </div>
      )}

      {/* Warning for large playlists */}
      {playlistInfo.total_tracks > 20 && (
        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="text-sm text-yellow-800">
            <strong>⚠️ Playlist grande:</strong> Esta descarga puede tomar varios minutos. 
            {playlistInfo.limited && " Se descargarán solo los primeros 50 tracks por seguridad."}
          </div>
        </div>
      )}

      {/* Platform-specific info */}
      {playlistInfo.platform === "spotify" && (
        <div className="text-xs text-muted-foreground">
          💡 Los tracks de Spotify se buscarán automáticamente en YouTube para la descarga
        </div>
      )}
    </Card>
  )
}
