import { type NextRequest } from "next/server"

const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://localhost:8000"

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ downloadId: string }> }
) {
  const { downloadId } = await params

  if (!downloadId) {
    return new Response("Download ID is required", { status: 400 })
  }

  try {
    console.log("[API] Starting progress stream for download ID:", downloadId)

    // Conectar al stream de progreso del backend
    const backendResponse = await fetch(
      `${BACKEND_API_URL}/api/v1/progress-stream/${downloadId}`,
      {
        method: "GET",
        headers: {
          "Accept": "text/event-stream",
          "Cache-Control": "no-cache",
        },
      }
    )

    if (!backendResponse.ok) {
      console.error("[API] Backend progress stream error:", backendResponse.status)
      return new Response("Error connecting to progress stream", { 
        status: backendResponse.status 
      })
    }

    // Crear un ReadableStream que reenvíe los datos del backend
    const stream = new ReadableStream({
      start(controller) {
        const reader = backendResponse.body?.getReader()
        
        if (!reader) {
          controller.close()
          return
        }

        const pump = async () => {
          try {
            while (true) {
              const { done, value } = await reader.read()
              
              if (done) {
                console.log("[API] Progress stream ended for:", downloadId)
                controller.close()
                break
              }
              
              // Reenviar los datos tal como vienen del backend
              controller.enqueue(value)
            }
          } catch (error) {
            console.error("[API] Error in progress stream:", error)
            controller.error(error)
          }
        }

        pump()
      },
      
      cancel() {
        console.log("[API] Progress stream cancelled for:", downloadId)
      }
    })

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Cache-Control",
      },
    })

  } catch (error) {
    console.error("[API] Progress stream error:", error)
    return new Response("Internal server error", { status: 500 })
  }
}
