import { type NextRequest, NextResponse } from "next/server"

const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://localhost:8000"

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const url = searchParams.get("url")

    if (!url) {
      return NextResponse.json({ error: "URL es requerida" }, { status: 400 })
    }

    console.log("[API] Getting playlist info for URL:", url)

    // Llamar al endpoint de información de playlist del backend
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 segundos timeout

    try {
      const backendResponse = await fetch(
        `${BACKEND_API_URL}/api/v1/playlist-info?url=${encodeURIComponent(url)}`,
        {
          method: "GET",
          headers: {
            "Accept": "application/json",
          },
          signal: controller.signal,
        }
      )

      clearTimeout(timeoutId)

      if (!backendResponse.ok) {
        const errorData = await backendResponse.json()
        console.error("[API] Backend playlist info error:", errorData)
        
        return NextResponse.json(
          { error: errorData.detail || errorData.error || "Error al obtener información del playlist" },
          { status: backendResponse.status }
        )
      }

      const result = await backendResponse.json()
      
      console.log("[API] Playlist info retrieved successfully:", result.info?.title || "Unknown")
      
      return NextResponse.json(result)

    } catch (error: any) {
      clearTimeout(timeoutId)
      
      if (error.name === 'AbortError') {
        console.error("[API] Playlist info request timeout")
        return NextResponse.json(
          { error: "Timeout al obtener información del playlist. Intenta nuevamente." },
          { status: 408 }
        )
      }
      
      throw error
    }

  } catch (error) {
    console.error("[API] Playlist info error:", error)
    return NextResponse.json(
      { error: "Error interno del servidor al obtener información del playlist" },
      { status: 500 }
    )
  }
}
