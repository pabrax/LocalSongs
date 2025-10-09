// Types for backend API integration

export interface DownloadRequest {
  url: string
  quality?: string
  output_format?: string
}

export interface DownloadResponse {
  success: boolean
  message?: string
  file_path?: string
  file_size?: number
  metadata?: {
    title?: string
    artist?: string
    duration?: number
    quality?: string
    platform?: string
  }
  error?: string
}

export interface HealthCheckResponse {
  status: string
  spotify_auth: boolean
  youtube_available: boolean
  output_directory: boolean
  message?: string
}

export interface QualitiesResponse {
  qualities: Array<{
    value: string
    label: string
    bitrate: string
  }>
}

export interface AudioInfoResponse {
  success: boolean
  metadata?: {
    title: string
    artist: string
    duration: number
    thumbnail?: string
    platform: string
  }
  error?: string
}