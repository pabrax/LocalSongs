"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { Download, Music, Loader2, CheckCircle2, AlertCircle, Disc3, Waves, Settings, Info } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { useDownload } from "@/hooks/use-download"
import type { AudioInfoResponse } from "@/types/api"

type DownloadStatus = "idle" | "loading" | "success" | "error" | "info-loading"

interface DownloadResult {
  fileName: string
  fileSize?: number
  metadata?: {
    title?: string
    artist?: string
    duration?: number
    quality?: string
    platform?: string
  }
}

const QUALITY_OPTIONS = [
  { value: "96", label: "96 kbps", description: "Baja calidad" },
  { value: "128", label: "128 kbps", description: "Calidad estándar" },
  { value: "192", label: "192 kbps", description: "Alta calidad" },
  { value: "320", label: "320 kbps", description: "Máxima calidad" },
]

export default function MusicDownloader() {
  const [url, setUrl] = useState("")
  const [quality, setQuality] = useState("192")
  const [status, setStatus] = useState<DownloadStatus>("idle")
  const [downloadResult, setDownloadResult] = useState<DownloadResult | null>(null)
  const [audioInfo, setAudioInfo] = useState<AudioInfoResponse | null>(null)
  const [backendStatus, setBackendStatus] = useState<"unknown" | "connected" | "disconnected">("unknown")

  const { isLoading, error, downloadFile, getAudioInfo, clearError } = useDownload()

  // Verificar estado del backend al cargar
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const response = await fetch("/api/health")
        const data = await response.json()
        setBackendStatus(response.ok ? "connected" : "disconnected")
      } catch {
        setBackendStatus("disconnected")
      }
    }

    checkBackendHealth()
  }, [])

  // Limpiar errores cuando cambia la URL
  useEffect(() => {
    if (error) {
      clearError()
    }
    setAudioInfo(null)
  }, [url, clearError, error])

  const validateUrl = (url: string): boolean => {
    const supportedPlatforms = [
      'youtube.com',
      'youtu.be', 
      'music.youtube.com',
      'open.spotify.com',
      'spotify.com'  // Añadido soporte adicional para spotify.com
    ]
    
    return supportedPlatforms.some(platform => 
      url.toLowerCase().includes(platform)
    )
  }

  const handleGetInfo = async () => {
    if (!url.trim()) return

    if (!validateUrl(url)) {
      setStatus("error")
      return
    }

    setStatus("info-loading")
    const info = await getAudioInfo(url)
    
    if (info && info.success) {
      setAudioInfo(info)
      setStatus("idle")
    } else {
      setStatus("error")
    }
  }

  const handleDownload = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!url.trim()) {
      setStatus("error")
      return
    }

    if (!validateUrl(url)) {
      setStatus("error")
      return
    }

    setStatus("loading")
    setDownloadResult(null)

    const success = await downloadFile(url, quality)
    
    if (success) {
      // Simular información del resultado (ya que el archivo se descargó)
      setDownloadResult({
        fileName: `audio_${quality}kbps.mp3`,
        metadata: {
          quality,
          platform: url.includes('spotify') ? 'Spotify' : 'YouTube'
        }
      })
      setStatus("success")
      
      setTimeout(() => {
        setStatus("idle")
        setUrl("")
        setDownloadResult(null)
        setAudioInfo(null)
      }, 5000)
    } else {
      setStatus("error")
    }
  }

  return (
    <main className="min-h-screen relative overflow-hidden flex flex-col items-center justify-center p-4">
      <div className="absolute inset-0 gradient-bg opacity-20" />

      <div className="absolute top-20 left-10 w-32 h-32 bg-primary/20 rounded-full blur-3xl glow-effect" />
      <div
        className="absolute bottom-20 right-10 w-40 h-40 bg-secondary/20 rounded-full blur-3xl glow-effect"
        style={{ animationDelay: "1s" }}
      />
      <div
        className="absolute top-1/2 left-1/4 w-24 h-24 bg-accent/20 rounded-full blur-3xl glow-effect"
        style={{ animationDelay: "2s" }}
      />

      <div className="relative z-10 w-full max-w-4xl">
        {/* Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-3 mb-6 float-animation">
            <Disc3 className="w-12 h-12 text-primary" strokeWidth={2} />
            <Waves className="w-12 h-12 text-secondary" strokeWidth={2} />
            <Music className="w-12 h-12 text-accent" strokeWidth={2} />
          </div>
          <h1 className="text-6xl md:text-8xl font-black mb-4 bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent">
            SoundDrop
          </h1>
          <p className="text-lg md:text-xl text-muted-foreground font-medium">
            Descarga tu música favorita de YouTube y Spotify
          </p>
          
          {/* Backend Status */}
          <div className="mt-4 flex justify-center">
            <Badge 
              variant={backendStatus === "connected" ? "default" : "destructive"}
              className="text-xs"
            >
              {backendStatus === "connected" ? "🟢 Conectado" : 
               backendStatus === "disconnected" ? "🔴 Backend desconectado" : 
               "🟡 Verificando..."}
            </Badge>
          </div>
        </div>

        <Card className="relative p-8 md:p-12 bg-card/80 backdrop-blur-xl border-2 border-primary/30 shadow-2xl shadow-primary/20">
          <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-primary via-secondary to-accent opacity-20 blur-xl" />

          <div className="relative">
            <form onSubmit={handleDownload} className="space-y-8">
              <div className="space-y-3">
                <label htmlFor="url" className="text-base font-bold text-foreground uppercase tracking-wide">
                  URL del Audio
                </label>
                <div className="relative">
                  <Input
                    id="url"
                    type="url"
                    placeholder="Ej: https://open.spotify.com/track/... o https://www.youtube.com/watch?v=..."
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={isLoading || status === "info-loading"}
                    className="h-14 text-base bg-muted/50 border-2 border-muted focus:border-primary transition-colors pl-4 pr-16"
                  />
                  {url && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={handleGetInfo}
                      disabled={status === "info-loading" || isLoading}
                      className="absolute right-2 top-2 h-10 px-3"
                    >
                      {status === "info-loading" ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Info className="w-4 h-4" />
                      )}
                    </Button>
                  )}
                </div>
              </div>

              {/* Audio Info Preview */}
              {audioInfo && audioInfo.success && audioInfo.metadata && (
                <div className="p-4 bg-muted/30 border border-muted rounded-lg">
                  <div className="flex items-center gap-3 mb-2">
                    <Music className="w-5 h-5 text-primary" />
                    <span className="font-semibold text-sm uppercase tracking-wide">Vista Previa</span>
                  </div>
                  <div className="space-y-2">
                    <p className="font-bold">{audioInfo.metadata.title}</p>
                    {audioInfo.metadata.artist && (
                      <p className="text-muted-foreground">{audioInfo.metadata.artist}</p>
                    )}
                    <div className="flex gap-2">
                      {audioInfo.metadata.platform && (
                        <Badge variant="secondary">{audioInfo.metadata.platform}</Badge>
                      )}
                      {audioInfo.metadata.duration && (
                        <Badge variant="outline">
                          {Math.floor(audioInfo.metadata.duration / 60)}:{(audioInfo.metadata.duration % 60).toString().padStart(2, '0')}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              )}

              <div className="space-y-3">
                <label className="text-base font-bold text-foreground uppercase tracking-wide flex items-center gap-2">
                  <Settings className="w-4 h-4" />
                  Calidad de Audio
                </label>
                <Select value={quality} onValueChange={setQuality} disabled={isLoading}>
                  <SelectTrigger className="h-14 text-base bg-muted/50 border-2 border-muted focus:border-primary">
                    <SelectValue placeholder="Selecciona la calidad" />
                  </SelectTrigger>
                  <SelectContent>
                    {QUALITY_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        <div className="flex items-center justify-between w-full">
                          <span className="font-medium">{option.label}</span>
                          <span className="text-sm text-muted-foreground ml-2">{option.description}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Button
                type="submit"
                disabled={isLoading || backendStatus !== "connected"}
                className="w-full h-14 text-lg font-bold bg-gradient-to-r from-primary via-secondary to-accent hover:opacity-90 transition-opacity shadow-lg shadow-primary/30"
                size="lg"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-6 h-6 mr-3 animate-spin" />
                    Procesando descarga...
                  </>
                ) : (
                  <>
                    <Download className="w-6 h-6 mr-3" />
                    Descargar Ahora
                  </>
                )}
              </Button>
            </form>

            {/* Success Message */}
            {status === "success" && downloadResult && (
              <div className="mt-8 p-5 bg-primary/20 border-2 border-primary rounded-lg backdrop-blur-sm">
                <div className="flex items-start gap-4">
                  <CheckCircle2 className="w-6 h-6 text-primary flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-base font-bold text-primary mb-2">¡Descarga exitosa!</p>
                    <p className="text-sm text-primary/80 mb-3">El archivo se ha descargado correctamente</p>
                    <div className="flex flex-wrap gap-2">
                      {downloadResult.metadata?.quality && (
                        <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20">
                          {downloadResult.metadata.quality} kbps
                        </Badge>
                      )}
                      {downloadResult.metadata?.platform && (
                        <Badge variant="secondary" className="bg-secondary/10 text-secondary border-secondary/20">
                          {downloadResult.metadata.platform}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Error Message */}
            {(status === "error" || error) && (
              <div className="mt-8 p-5 bg-destructive/20 border-2 border-destructive rounded-lg flex items-start gap-4 backdrop-blur-sm">
                <AlertCircle className="w-6 h-6 text-destructive flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-base font-bold text-destructive">Error</p>
                  <p className="text-sm text-destructive/80 mt-1">
                    {error || 
                     (!validateUrl(url) && url ? "URL no soportada. Usa: open.spotify.com/track/..., youtube.com/watch?v=..., o music.youtube.com/watch?v=..." : 
                      "No se pudo procesar la solicitud. Verifica la URL e intenta nuevamente.")}
                  </p>
                </div>
              </div>
            )}
          </div>
        </Card>

        <div className="mt-12 flex flex-wrap items-center justify-center gap-4">
          <div className="px-4 py-2 bg-primary/20 border border-primary/40 rounded-full backdrop-blur-sm">
            <p className="text-sm font-bold text-primary">YouTube • Spotify</p>
          </div>
          <div className="px-4 py-2 bg-secondary/20 border border-secondary/40 rounded-full backdrop-blur-sm">
            <p className="text-sm font-bold text-secondary">MP3 Alta Calidad</p>
          </div>
          <div className="px-4 py-2 bg-accent/20 border border-accent/40 rounded-full backdrop-blur-sm">
            <p className="text-sm font-bold text-accent">100% Seguro</p>
          </div>
        </div>
      </div>
    </main>
  )
}
