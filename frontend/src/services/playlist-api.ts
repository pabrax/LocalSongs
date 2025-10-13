/**
 * API service for playlist operations
 */

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

export interface PlaylistDownloadResponse {
  download_id: string
  message: string
  progress_url: string
  total_files: number
  playlist_info: PlaylistInfo
  zip_file?: string
}

export class PlaylistApiService {
  private baseUrl: string

  constructor(baseUrl: string = '/api') {
    this.baseUrl = baseUrl
  }

  async getPlaylistInfo(url: string) {
    const response = await fetch(`${this.baseUrl}/v1/playlist-info`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url }),
    })

    if (!response.ok) {
      throw new Error(`Failed to get playlist info: ${response.statusText}`)
    }

    return response.json()
  }

  async downloadPlaylist(url: string, quality: string = '192') {
    const response = await fetch(`${this.baseUrl}/v1/multi-download`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url,
        quality: { value: quality }
      }),
    })

    if (!response.ok) {
      throw new Error(`Playlist download failed: ${response.statusText}`)
    }

    return response.json()
  }

  async createZip(downloadId: string) {
    const response = await fetch(`${this.baseUrl}/v1/create-zip/${downloadId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`ZIP creation failed: ${response.statusText}`)
    }

    return response.json()
  }

  async cleanupFiles(downloadId: string, keepZip: boolean = true) {
    const response = await fetch(`${this.baseUrl}/v1/cleanup/${downloadId}?keep_zip=${keepZip}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`Cleanup failed: ${response.statusText}`)
    }

    return response.json()
  }

  getProgressStream(downloadId: string): EventSource {
    return new EventSource(`${this.baseUrl}/v1/multi-progress/${downloadId}`)
  }
}