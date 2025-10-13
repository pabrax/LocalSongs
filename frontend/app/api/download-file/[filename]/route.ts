import { type NextRequest } from "next/server"

const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://localhost:8000"

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ filename: string }> }
) {
  const { filename } = await params

  if (!filename) {
    return new Response("Filename is required", { status: 400 })
  }

  try {
    console.log("[API] Downloading file:", filename)

    // Obtener el archivo del backend
    const backendResponse = await fetch(
      `${BACKEND_API_URL}/api/v1/download-file/${encodeURIComponent(filename)}`,
      {
        method: "GET",
      }
    )

    if (!backendResponse.ok) {
      console.error("[API] Backend file download error:", backendResponse.status)
      
      if (backendResponse.status === 404) {
        return new Response("File not found", { status: 404 })
      }
      
      return new Response("Error downloading file from backend", { 
        status: backendResponse.status 
      })
    }

    // Obtener el contenido del archivo
    const fileBuffer = await backendResponse.arrayBuffer()
    const contentType = backendResponse.headers.get("content-type") || "audio/mpeg"
    const contentDisposition = backendResponse.headers.get("content-disposition") || 
                              `attachment; filename="${filename}"`

    console.log("[API] File downloaded successfully:", filename, "Size:", fileBuffer.byteLength)

    return new Response(fileBuffer, {
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": contentDisposition,
        "Content-Length": fileBuffer.byteLength.toString(),
        "Cache-Control": "no-cache",
      },
    })

  } catch (error) {
    console.error("[API] File download error:", error)
    return new Response("Internal server error", { status: 500 })
  }
}
