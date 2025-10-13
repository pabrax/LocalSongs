import { type NextRequest, NextResponse } from "next/server"

const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://localhost:8000"

export async function POST(request: NextRequest) {
  try {
    const { url, quality = "192", output_format = "mp3" } = await request.json()

    if (!url) {
      return NextResponse.json({ error: "URL es requerida" }, { status: 400 })
    }

    console.log("[API] Starting download with progress for URL:", url, "with quality:", quality)

    // Llamar al endpoint de descarga con progreso del backend
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 segundos timeout para iniciar

    try {
      const downloadResponse = await fetch(`${BACKEND_API_URL}/api/v1/download-with-progress`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url,
          quality,
          output_format
        }),
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!downloadResponse.ok) {
        const errorData = await downloadResponse.json()
        console.error("[API] Backend error:", errorData)
        
        return NextResponse.json(
          { error: errorData.detail || errorData.error || "Error al iniciar la descarga en el backend" },
          { status: downloadResponse.status }
        )
      }

      const result = await downloadResponse.json()
      
      console.log("[API] Download initiated successfully:", result.download_id)
      
      return NextResponse.json(result)

    } catch (error: any) {
      clearTimeout(timeoutId)
      
      if (error.name === 'AbortError') {
        console.error("[API] Request timeout")
        return NextResponse.json(
          { error: "Timeout al iniciar la descarga. Intenta nuevamente." },
          { status: 408 }
        )
      }
      
      throw error
    }

  } catch (error) {
    console.error("[API] Download with progress error:", error)
    return NextResponse.json(
      { error: "Error interno del servidor al iniciar la descarga" },
      { status: 500 }
    )
  }
}
