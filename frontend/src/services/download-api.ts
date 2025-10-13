/**
 * API service for download operations
 */

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
  download_id?: string
}

export class DownloadApiService {
  private baseUrl: string

  constructor(baseUrl: string = '/api') {
    this.baseUrl = baseUrl
  }

  async downloadAudio(request: DownloadRequest): Promise<DownloadResponse> {
    const response = await fetch(`${this.baseUrl}/v1/download`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`)
    }

    return response.json()
  }

  async getAudioInfo(url: string) {
    const response = await fetch(`${this.baseUrl}/v1/audio-info`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url }),
    })

    if (!response.ok) {
      throw new Error(`Failed to get audio info: ${response.statusText}`)
    }

    return response.json()
  }

  async downloadWithProgress(request: DownloadRequest) {
    const response = await fetch(`${this.baseUrl}/v1/download-with-progress`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`)
    }

    return response.json()
  }

  async healthCheck() {
    const response = await fetch(`${this.baseUrl}/health`)
    return response.json()
  }
}