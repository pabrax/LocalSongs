import { type NextRequest, NextResponse } from "next/server"

const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://localhost:8000"

export async function POST(request: NextRequest) {
  try {
    const { url, quality = "192", output_format = "mp3" } = await request.json()

    if (!url) {
      return NextResponse.json({ error: "URL es requerida" }, { status: 400 })
    }

    console.log("[API] Starting playlist download for URL:", url, "with quality:", quality)

    // Llamar al endpoint de descarga de playlist del backend
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 segundos timeout para iniciar

    try {
      console.log("[API] Starting playlist download request to backend...")
      
      const downloadResponse = await fetch(`${BACKEND_API_URL}/api/v1/download-playlist`, {
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

      console.log("[API] Backend response status:", downloadResponse.status)
      console.log("[API] Backend response headers:", Object.fromEntries(downloadResponse.headers))

      clearTimeout(timeoutId)

      if (!downloadResponse.ok) {
        let errorData: any = {}
        
        try {
          // Intentar parsear como JSON
          const responseText = await downloadResponse.text()
          console.log("[API] Backend response text:", responseText)
          
          if (responseText.trim().startsWith('{') || responseText.trim().startsWith('[')) {
            errorData = JSON.parse(responseText)
          } else {
            // Si no es JSON, usar el texto como mensaje de error
            errorData = { error: responseText }
          }
        } catch (parseError) {
          console.error("[API] Error parsing backend response:", parseError)
          errorData = { error: `Error del servidor (${downloadResponse.status})` }
        }
        
        console.error("[API] Backend playlist download error:", errorData)
        
        return NextResponse.json(
          { error: errorData.detail || errorData.error || "Error al iniciar la descarga del playlist" },
          { status: downloadResponse.status }
        )
      }

      let result: any = {}
      
      try {
        const responseText = await downloadResponse.text()
        console.log("[API] Backend success response text (first 200 chars):", responseText.substring(0, 200))
        
        if (responseText.trim().startsWith('{') || responseText.trim().startsWith('[')) {
          result = JSON.parse(responseText)
        } else {
          console.error("[API] Response is not JSON. Full response:", responseText)
          return NextResponse.json(
            { error: "El servidor devolvió una respuesta inválida (no JSON)" },
            { status: 500 }
          )
        }
      } catch (parseError) {
        console.error("[API] Error parsing success response:", parseError)
        return NextResponse.json(
          { error: "Error parsing server response" },
          { status: 500 }
        )
      }
      
      console.log("[API] Playlist download initiated successfully:", result.download_id, `(${result.total_files} files)`)
      
      return NextResponse.json(result)

    } catch (error: any) {
      clearTimeout(timeoutId)
      
      console.error("[API] Playlist download fetch error:", error)
      
      if (error.name === 'AbortError') {
        console.error("[API] Playlist download request timeout")
        return NextResponse.json(
          { error: "Timeout al iniciar la descarga del playlist. Intenta nuevamente." },
          { status: 408 }
        )
      }
      
      // Check if it's a network error
      if (error.code === 'ECONNREFUSED' || error.message?.includes('fetch')) {
        return NextResponse.json(
          { error: "No se puede conectar al backend. Verifica que esté ejecutándose." },
          { status: 503 }
        )
      }
      
      return NextResponse.json(
        { error: `Error de red: ${error.message || 'Error desconocido'}` },
        { status: 500 }
      )
    }

  } catch (error) {
    console.error("[API] Playlist download error:", error)
    return NextResponse.json(
      { error: "Error interno del servidor al iniciar la descarga del playlist" },
      { status: 500 }
    )
  }
}
