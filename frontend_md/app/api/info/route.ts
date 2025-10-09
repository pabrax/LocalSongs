import { type NextRequest, NextResponse } from "next/server"

const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://localhost:8000"

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const url = searchParams.get('url')

    if (!url) {
      return NextResponse.json({ error: "URL es requerida" }, { status: 400 })
    }

    console.log("[API] Getting info for URL:", url)

    const response = await fetch(`${BACKEND_API_URL}/api/v1/info?url=${encodeURIComponent(url)}`)

    if (!response.ok) {
      const errorData = await response.json()
      console.error("[API] Backend error:", errorData)
      return NextResponse.json(
        { error: errorData.error || "Error al obtener información del audio" },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error("[API] Info error:", error)
    return NextResponse.json(
      { error: "Error interno del servidor al obtener información" },
      { status: 500 }
    )
  }
}