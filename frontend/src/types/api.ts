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
  download_id?: string  // ID para tracking de progreso
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

// Tipos para el sistema de progreso
export interface ProgressData {
  progress: number
  status: string
  message: string
  error?: string
  filename?: string
  timestamp?: number
}

export interface DownloadWithProgressResponse {
  download_id: string
  message: string
  progress_url: string
}

export interface ProgressStreamEvent {
  data: ProgressData
}

// Tipos para el sistema de progreso multi-archivo
export interface PlaylistInfo {
  type: "track" | "album" | "playlist"
  platform: string
  total_tracks: number
  tracks: string[]
  url: string
  title: string
  uploader?: string
  limited: boolean
}

export interface PlaylistInfoResponse {
  success: boolean
  info: PlaylistInfo
}

export interface FileInfo {
  index: number
  name: string
  status: "pending" | "downloading" | "completed" | "failed"
  progress: number
  error?: string
  message?: string
}

export interface MultiProgressData {
  download_id: string
  total_files: number
  completed_files: number
  failed_files: number
  current_file_index: number
  current_file_progress: number
  current_file_name: string
  current_file_status: string
  overall_progress: number
  overall_status: string
  message: string
  error?: string
  files_info: FileInfo[]
  timestamp: number
}

export interface PlaylistDownloadResponse {
  download_id: string
  message: string
  progress_url: string
  total_files: number
  playlist_info: PlaylistInfo
  zip_file?: string  // Path to ZIP file when playlist is complete
}

// Tipos para archivos descargados
export interface DownloadedFile {
  name: string
  size: number
  path: string
  folder?: string
}

export interface ListFilesResponse {
  success: boolean
  files: DownloadedFile[]
  count: number
  folder?: string
  error?: string
}

// Tipos para descarga de ZIP
export interface ZipDownloadResponse {
  success: boolean
  zip_file?: string
  download_url?: string
  file_size?: number
  error?: string
}