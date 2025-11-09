"""
Main FastAPI application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os

# Importar configuración
from src.utils.config import get_settings

app = FastAPI(
    title="Text-to-Report Chatbot API",
    description="API para generar reportes a partir de consultas en lenguaje natural",
    version="0.1.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Endpoint de bienvenida"""
    return {"message": "¡Bienvenido al Text-to-Report Chatbot API!"}

@app.get("/api/v1/health")
async def health_check():
    """Endpoint de verificación de salud"""
    try:
        settings = get_settings()
        return {
            "status": "healthy",
            "version": "0.1.0",
            "model": settings.openai_model,
            "environment": "development" if settings.debug else "production"
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

@app.get("/api/v1/config")
async def get_config():
    """Endpoint para obtener configuración (sin datos sensibles)"""
    try:
        settings = get_settings()
        return {
            "app_name": settings.app_name,
            "model": settings.openai_model,
            "temperature": settings.openai_temperature,
            "debug": settings.debug,
            "api_key_configured": bool(settings.openai_api_key and len(settings.openai_api_key) > 10)
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Error al obtener configuración: {str(e)}"
            }
        )

@app.post("/api/v1/chat")
async def chat_endpoint(message: dict):
    """Endpoint principal para el chat"""
    try:
        # TODO: Implementar la lógica del chat con los agentes
        return {
            "message": "Endpoint en desarrollo",
            "received": message,
            "status": "pending_implementation"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Error en el chat: {str(e)}"
            }
        )

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )