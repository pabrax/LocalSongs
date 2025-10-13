import { type NextRequest, NextResponse } from "next/server"

const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://localhost:8000"

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const folder = searchParams.get('folder')

    if (!folder) {
      return NextResponse.json({ error: "Folder parameter is required" }, { status: 400 })
    }

    console.log("[API] Listing downloaded files for folder:", folder)

    // Llamar al endpoint del backend para listar archivos
    const response = await fetch(`${BACKEND_API_URL}/api/v1/list-files?folder=${encodeURIComponent(folder)}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: "Unknown error" }))
      console.error("[API] Backend list files error:", errorData)
      
      return NextResponse.json(
        { error: errorData.detail || errorData.error || "Error listing files" },
        { status: response.status }
      )
    }

    const result = await response.json()
    console.log("[API] Files listed successfully:", result.files?.length || 0, "files")
    
    return NextResponse.json(result)

  } catch (error) {
    console.error("[API] List files error:", error)
    return NextResponse.json(
      { error: "Internal server error listing files" },
      { status: 500 }
    )
  }
}