# LocalSongs

> **Un descargador de música moderno y completo con soporte para múltiples plataformas**

LocalSongs es una aplicación web full-stack que permite descargar música de alta calidad desde YouTube, YouTube Music y Spotify. Construida con tecnologías modernas, ofrece una experiencia de usuario fluida con progreso en tiempo real y organización automática de archivos.

## Vista Previa de la Aplicación

![LocalSongs App Screenshot](./Docs/images/localsongs.jpeg)

## Características Principales

### **Funcionalidades Core**
- **Descarga Multi-plataforma**: YouTube, YouTube Music, Spotify y URLs internacionales
- **Calidad de Audio Variable**: 96kbps hasta 320kbps según preferencias
- **Progreso en Tiempo Real**: Seguimiento visual de cada descarga con SSE
- **Albums y Playlists Completos**: Descarga automática de colecciones enteras
- **Organización Inteligente**: Carpetas automáticas por album/playlist/artista

### **Características Técnicas**
- **Backend Robusto**: FastAPI con operaciones asíncronas y manejo de timeouts
- **Frontend Moderno**: Next.js 15+ con TypeScript y Tailwind CSS
- **Corrección Automática**: Detección y reparación de extensiones problemáticas
- **Cancelación Granular**: Control total sobre descargas en progreso
- **Gestión de Errores**: Sistema comprensivo de logging y recuperación

## Inicio Rápido

### Prerrequisitos
- **Python 3.13+** con gestor de paquetes [uv](https://github.com/astral-sh/uv)
- **Node.js 18+** con **pnpm**
- **FFmpeg** instalado en el sistema
- **spotdl** para descarga de Spotify

### Instalación

#### 1. Clonar el repositorio
```bash
git clone https://github.com/pabrax/LocalSongs.git
cd LocalSongs
```

#### 2. Configurar Backend
```bash
cd backend
uv sync
```

#### 3. Configurar Frontend
```bash
cd ../frontend
pnpm install
```

### Ejecución

#### Backend (Terminal 1)
```bash
cd backend
uv run python main.py
```

#### Frontend (Terminal 2)
```bash
cd frontend
pnpm dev
```

**Acceder a la aplicación:** [http://localhost:3000](http://localhost:3000)

**Documentación API:** [http://localhost:8000/docs](http://localhost:8000/docs)

## Características Avanzadas

### **Descarga de Colecciones Completas**
LocalSongs puede descargar albums y playlists completos con organización automática:

```
downloads/
├── [Nombre del Album] [album] [spotify]/
│   ├── 01 - Artista - Canción 1 [192kbps].mp3
│   ├── 02 - Artista - Canción 2 [192kbps].mp3
│   └── ...
├── [Nombre Playlist] [playlist] [youtube]/
│   └── Individual tracks...
└── Descargas individuales...
```

### **Progreso en Tiempo Real**
- **Progreso global** para albums/playlists completos
- **Progreso individual** por cada archivo
- **Estados detallados**: preparando → descargando → convirtiendo → completado
- **Cancelación en tiempo real** de descargas activas

### **URLs Soportadas**

| Plataforma | Tipo | Ejemplo |
|------------|------|---------|
| **Spotify** | Track | `https://open.spotify.com/track/...` |
| **Spotify** | Album | `https://open.spotify.com/album/...` |
| **Spotify** | Playlist | `https://open.spotify.com/playlist/...` |
| **YouTube** | Video | `https://www.youtube.com/watch?v=...` |
| **YouTube** | Playlist | `https://www.youtube.com/playlist?list=...` |
| **YT Music** | Track | `https://music.youtube.com/watch?v=...` |

### **Calidades de Audio**
- **96 kbps** - Calidad básica, archivos pequeños
- **128 kbps** - Calidad estándar
- **192 kbps** - Calidad alta (predeterminado)
- **320 kbps** - Calidad máxima

## Arquitectura del Proyecto

```
LocalSongs/
├── backend/                  # Backend FastAPI
│   ├── src/
│   │   ├── api/                 # Endpoints de API
│   │   ├── core/                # Configuración y utilidades
│   │   ├── services/            # Lógica de descarga
│   │   ├── schemas/             # Esquemas de datos
│   │   └── main.py             # Aplicación principal
│   ├── downloads/              # Archivos descargados
│   ├── main.py                 # Punto de entrada
│   └── pyproject.toml          # Configuración uv
├── frontend/                 # Frontend Next.js
│   ├── app/                     # App Router de Next.js
│   ├── src/
│   │   ├── components/          # Componentes React
│   │   ├── hooks/               # Hooks personalizados
│   │   ├── services/            # Servicios API
│   │   └── types/               # Tipos TypeScript
│   └── package.json            # Dependencias Node.js
├── Docs/                     # Documentación y assets
└── README.md                 # Esta documentación
```

## Configuración Avanzada

### Variables de Entorno
Crea un archivo `.env` en el directorio `backend/`:

```env
# Configuración opcional de Spotify (para mejor metadata)
SPOTIFY_CLIENT_ID=tu_client_id
SPOTIFY_CLIENT_SECRET=tu_client_secret

# Directorio de descargas personalizado
DOWNLOADS_DIR=./downloads

# Configuración de timeouts
DOWNLOAD_TIMEOUT=300
INFO_TIMEOUT=30
```

### Configuración del Backend
Edita `backend/src/core/config.py` para personalizar:

```python
class Settings(BaseSettings):
    # Directorio de descargas
    downloads_dir: str = "./downloads"
    
    # Calidad predeterminada
    default_quality: str = "192"
    
    # Tamaño máximo de archivo (MB)
    max_file_size_mb: int = 100
    
    # Formatos permitidos
    allowed_formats: list = ["mp3", "wav", "flac"]
```

## Pruebas y Diagnóstico

### Verificación del Sistema
```bash
# Verificar que spotdl esté instalado
spotdl --version

# Verificar configuración del backend
cd backend && uv run python -c "from src.main import app; print('✅ Backend OK')"

# Verificar configuración del frontend
cd frontend && pnpm run type-check
```

## API Reference

### Endpoints Principales

#### Descarga Individual
```http
POST /api/v1/download
Content-Type: application/json

{
  "url": "https://open.spotify.com/track/...",
  "quality": "192",
  "output_format": "mp3"
}
```

#### Descarga con Progreso
```http
POST /api/v1/download-with-progress
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=...",
  "quality": "320"
}
```

#### Información de Playlist
```http
GET /api/v1/playlist-info?url=https://open.spotify.com/album/...
```

#### Descarga de Playlist
```http
POST /api/v1/download-playlist
Content-Type: application/json

{
  "url": "https://open.spotify.com/album/...",
  "quality": "192"
}
```

### Respuestas de la API

#### Descarga Exitosa
```json
{
  "success": true,
  "message": "Descarga completada exitosamente",
  "file_path": "downloads/Artista - Canción [192kbps].mp3",
  "file_size": 5242880,
  "metadata": {
    "title": "Nombre de la Canción",
    "artist": "Nombre del Artista",
    "duration": 210,
    "quality": "192kbps",
    "platform": "spotify"
  }
}
```

#### Información de Playlist
```json
{
  "type": "album",
  "platform": "spotify", 
  "title": "Nombre del Album",
  "total_tracks": 12,
  "tracks": [
    "Artista - Canción 1",
    "Artista - Canción 2",
    "..."
  ],
  "limited": false
}
```

## Desarrollo y Contribución

### Entorno de Desarrollo

#### Backend Development
```bash
cd backend

# Modo desarrollo con auto-reload
uv run python main.py

# Agregar dependencias
uv add nombre_paquete

# Actualizar dependencias
uv sync
```

#### Frontend Development
```bash
cd frontend

# Servidor de desarrollo con hot reload
pnpm dev

# Verificación de tipos
pnpm run type-check

# Linting y formato
pnpm run lint
```

### Despliegue en Producción

#### Backend
```bash
cd backend

# Instalar dependencias de producción
uv sync --no-dev

# Ejecutar servidor de producción
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Frontend
```bash
cd frontend

# Build para producción
pnpm build

# Servidor de producción
pnpm start
```

### Cómo Contribuir

1. **Fork** del repositorio
2. **Crear branch** de funcionalidad: `git checkout -b feature/nueva-funcionalidad`
3. **Commit** de cambios: `git commit -m 'Agregar nueva funcionalidad'`
4. **Push** al branch: `git push origin feature/nueva-funcionalidad`
5. **Crear Pull Request**

### Áreas de Contribución
- Corrección de bugs y mejoras de estabilidad
- Nuevas funcionalidades y características
- Documentación y tutoriales
- Pruebas y scripts de validación
- Mejoras de UI/UX y diseño

## Solución de Problemas

### Errores Comunes

#### Backend no inicia
```bash
# Verificar instalación de UV
uv --version

# Reinstalar dependencias
cd backend && rm -rf .venv && uv sync

# Verificar Python
python3 --version  # Debería ser 3.13+
```

#### Frontend no inicia
```bash
# Verificar instalación de pnpm
pnpm --version

# Limpiar cache y reinstalar
cd frontend && rm -rf node_modules && pnpm install
```

#### Puertos ocupados
```bash
# Liberar puerto 8000 (backend)
lsof -ti:8000 | xargs kill -9

# Liberar puerto 3000 (frontend)
lsof -ti:3000 | xargs kill -9
```

### Diagnóstico Avanzado
```bash
# Verificar spotdl
spotdl --version

# Verificar conexión del backend
curl http://localhost:8000/health

# Ver logs detallados
# Los logs aparecen en la terminal donde ejecutaste main.py
```

## Stack Tecnológico

### Backend
- **FastAPI** - Framework web moderno y rápido
- **Python 3.13+** - Lenguaje de programación
- **UV** - Gestor de paquetes rápido para Python
- **spotdl** - Librería para descarga de Spotify
- **yt-dlp** - Herramienta para descarga de YouTube
- **asyncio** - Programación asíncrona

### Frontend
- **Next.js 15+** - Framework React con App Router
- **TypeScript 5** - JavaScript con tipado estático
- **Tailwind CSS 4** - Framework CSS utility-first
- **React 19** - Librería de componentes
- **pnpm** - Gestor de paquetes rápido

### Dependencias Clave
```json
{
  "backend": [
    "fastapi>=0.103.2", "uvicorn>=0.23.2", "spotdl>=4.4.2", 
    "yt-dlp>=2025.9.26", "pydantic-settings>=2.11.0", "ffmpeg-python>=0.2.0"
  ],
  "frontend": [
    "next@15.2.4", "react@19", "typescript@5",
    "@radix-ui/react-*", "lucide-react", "tailwindcss@4.1.9"
  ]
}
```

## Métricas del Proyecto

### Estadísticas de Código
- **~3,000 líneas** de código total (reorganizado y optimizado)
- **10+ endpoints** API documentados
- **4 calidades** de audio soportadas (96, 128, 192, 320 kbps)
- **3 plataformas** principales soportadas (Spotify, YouTube, YouTube Music)
- **Arquitectura modular** con separación de responsabilidades

### Rendimiento
- **<2 segundos** tiempo promedio de inicio de descarga
- **Progreso en tiempo real** con actualizaciones cada 500ms
- **Descarga directa** usando spotdl subprocess (más rápido y confiable)
- **Corrección automática** de extensiones problemáticas

## Licencia y Disclaimer

### Licencia
Este proyecto está licenciado bajo los términos especificados en [LICENSE](LICENSE).

### Uso Responsable
**Esta herramienta es para uso educativo y personal únicamente.** 

- Respeta los derechos de autor y términos de servicio de las plataformas
- Asegúrate de tener derecho a descargar y usar el contenido
- No uses esta herramienta para piratería o distribución no autorizada
- El proyecto no se hace responsable del uso indebido de la herramienta

## Enlaces Útiles

- **Documentación API**: [http://localhost:8000/docs](http://localhost:8000/docs) (cuando el servidor esté ejecutándose)
- **Reportar bugs**: [GitHub Issues](https://github.com/pabrax/LocalSongs/issues)
- **Discusiones**: [GitHub Discussions](https://github.com/pabrax/LocalSongs/discussions)
- **spotdl Documentation**: [https://github.com/spotDL/spotify-downloader](https://github.com/spotDL/spotify-downloader)

## Agradecimientos

- **spotdl** - Por la excelente integración con Spotify
- **yt-dlp** - Por el robusto soporte de YouTube  
- **FastAPI** - Por el framework backend moderno
- **Next.js** - Por el framework frontend excepcional
- **Comunidad Open Source** - Por las herramientas y librerías

---

<div align="center">

**Desarrollado con ❤️ por [pabrax](https://github.com/pabrax)**

![Made with FastAPI](https://img.shields.io/badge/Made%20with-FastAPI-009688.svg?style=flat-square&logo=fastapi)
![Made with Next.js](https://img.shields.io/badge/Made%20with-Next.js-000000.svg?style=flat-square&logo=next.js)
![Made with TypeScript](https://img.shields.io/badge/Made%20with-TypeScript-3178C6.svg?style=flat-square&logo=typescript)

**¡Si te gusta este proyecto, considera darle una estrella!**

</div>