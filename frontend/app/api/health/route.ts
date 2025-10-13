import { type NextRequest, NextResponse } from "next/server"

const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://localhost:8000"

export async function GET() {
  try {
    console.log("[API] Checking backend health...")

    const response = await fetch(`${BACKEND_API_URL}/api/v1/health`, {
      cache: 'no-store'
    })

    if (!response.ok) {
      return NextResponse.json(
        { 
          status: "error", 
          message: "Backend no disponible",
          backend_status: response.status 
        },
        { status: 503 }
      )
    }

    const data = await response.json()
    return NextResponse.json({
      status: "ok",
      backend: data,
      message: "Frontend y backend conectados correctamente"
    })

  } catch (error) {
    console.error("[API] Health check error:", error)
    return NextResponse.json(
      { 
        status: "error", 
        message: "Error al conectar con el backend",
        error: error instanceof Error ? error.message : "Unknown error"
      },
      { status: 503 }
    )
  }
}