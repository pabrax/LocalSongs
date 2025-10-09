import { type NextRequest, NextResponse } from "next/server"

const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://localhost:8000"

export async function POST(request: NextRequest) {
  try {
    const { url, quality = "192", output_format = "mp3" } = await request.json()

    if (!url) {
      return NextResponse.json({ error: "URL es requerida" }, { status: 400 })
    }

    console.log("[API] Downloading from URL:", url, "with quality:", quality)

    // Primero llamamos al endpoint de descarga del backend con timeout personalizado
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 300000) // 5 minutos timeout

    try {
      const downloadResponse = await fetch(`${BACKEND_API_URL}/api/v1/download`, {
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
        
        // Manejo específico de errores
        if (downloadResponse.status === 408) {
          return NextResponse.json(
            { error: "La descarga está tomando demasiado tiempo. Intenta con un video más corto o verifica tu conexión." },
            { status: 408 }
          )
        }
        
        return NextResponse.json(
          { error: errorData.detail || errorData.error || "Error al procesar la descarga en el backend" },
          { status: downloadResponse.status }
        )
      }

      const downloadResult = await downloadResponse.json()
      
      if (!downloadResult.success) {
        return NextResponse.json(
          { error: downloadResult.error || "Error en la descarga" },
          { status: 400 }
        )
      }

      // Extraer el nombre del archivo del path devuelto por el backend
      const filePath = downloadResult.file_path
      const fileName = filePath.split('/').pop() || "audio.mp3"
      
      console.log("[API] File downloaded successfully:", fileName)
      
      // Ahora descargamos el archivo usando el endpoint de descarga de archivo
      const fileResponse = await fetch(`${BACKEND_API_URL}/api/v1/download-file/${encodeURIComponent(fileName)}`)

      if (!fileResponse.ok) {
        console.error("[API] Error downloading file:", fileName)
        return NextResponse.json(
          { error: "Error al descargar el archivo procesado" },
          { status: 500 }
        )
      }

      const fileBuffer = await fileResponse.arrayBuffer()
      const contentType = fileResponse.headers.get("content-type") || "audio/mpeg"

      return new NextResponse(fileBuffer, {
        headers: {
          "Content-Type": contentType,
          "Content-Disposition": `attachment; filename="${fileName}"`,
          "Content-Length": fileBuffer.byteLength.toString(),
        },
      })

    } catch (error: any) {
      clearTimeout(timeoutId)
      
      if (error.name === 'AbortError') {
        console.error("[API] Request timeout")
        return NextResponse.json(
          { error: "La descarga está tomando demasiado tiempo. Intenta con un video más corto." },
          { status: 408 }
        )
      }
      
      throw error
    }

  } catch (error) {
    console.error("[API] Download error:", error)
    return NextResponse.json(
      { error: "Error interno del servidor al procesar la descarga" },
      { status: 500 }
    )
  }
}
