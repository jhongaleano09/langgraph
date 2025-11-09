"""
Configuración principal de la aplicación
"""
import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración de la aplicación usando Pydantic Settings"""
    
    # Información de la aplicación
    app_name: str = Field(default="Text-to-Report Chatbot", env="APP_NAME")
    app_version: str = Field(default="0.1.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Configuración del servidor
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    
    # LangGraph API
    langgraph_api_host: str = Field(default="0.0.0.0", env="LANGGRAPH_API_HOST")
    langgraph_api_port: int = Field(default=8123, env="LANGGRAPH_API_PORT")
    
    # Configuración de LLM
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    # Configuración del modelo OpenAI
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.1, env="OPENAI_TEMPERATURE")
    openai_max_tokens: Optional[int] = Field(default=None, env="OPENAI_MAX_TOKENS")
    
    # LangSmith
    langsmith_api_key: Optional[str] = Field(default=None, env="LANGSMITH_API_KEY")
    langsmith_tracing: bool = Field(default=False, env="LANGSMITH_TRACING")
    
    # Base de datos
    database_url: str = Field(..., env="DATABASE_URL")
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(..., env="DB_NAME")
    db_user: str = Field(..., env="DB_USER")
    db_password: str = Field(..., env="DB_PASSWORD")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # Configuración de API
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    secret_key: str = Field(..., env="SECRET_KEY")
    
    # Timeouts y límites
    max_query_timeout: int = Field(default=300, env="MAX_QUERY_TIMEOUT")  # 5 minutos
    max_iterations: int = Field(default=3, env="MAX_ITERATIONS")
    max_file_size: int = Field(default=10485760, env="MAX_FILE_SIZE")  # 10MB
    
    # Directorios
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    temp_dir: str = Field(default="./temp", env="TEMP_DIR")
    static_dir: str = Field(default="./static", env="STATIC_DIR")
    pdf_output_dir: str = Field(default="./generated_reports", env="PDF_OUTPUT_DIR")
    pdf_template_dir: str = Field(default="./templates", env="PDF_TEMPLATE_DIR")
    
    # Configuración de gráficos
    chart_dpi: int = Field(default=300, env="CHART_DPI")
    chart_format: str = Field(default="png", env="CHART_FORMAT")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    access_log: bool = Field(default=True, env="ACCESS_LOG")
    
    # CORS
    cors_origins: list = Field(
        default=["http://localhost:3000", "http://localhost:8080"], 
        env="CORS_ORIGINS"
    )
    
    # Seguridad
    allowed_hosts: list = Field(
        default=["localhost", "127.0.0.1"], 
        env="ALLOWED_HOSTS"
    )
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    prometheus_port: int = Field(default=8001, env="PROMETHEUS_PORT")
    
    # Azure específico (producción)
    azure_storage_connection_string: Optional[str] = Field(
        default=None, 
        env="AZURE_STORAGE_CONNECTION_STRING"
    )
    azure_storage_container: str = Field(default="reports", env="AZURE_STORAGE_CONTAINER")
    domain_name: Optional[str] = Field(default=None, env="DOMAIN_NAME")
    
    # Desarrollo
    reload: bool = Field(default=False, env="RELOAD")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instancia global de configuración
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Obtiene la configuración global de la aplicación
    Implementa patrón singleton para evitar múltiples cargas
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Recarga la configuración (útil para tests)"""
    global _settings
    _settings = None
    return get_settings()


# Configuración de logging
def setup_logging():
    """Configura el sistema de logging"""
    import logging.config
    
    settings = get_settings()
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[{levelname}] {asctime} - {name} - {message}",
                "style": "{",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "[{levelname}] {asctime} - {name}:{lineno} - {funcName} - {message}",
                "style": "{",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": settings.log_level,
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "detailed",
                "level": "INFO",
                "filename": "logs/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },
        "loggers": {
            "": {  # root logger
                "level": settings.log_level,
                "handlers": ["console"],
            },
            "src": {
                "level": settings.log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }
    
    # Crear directorio de logs si no existe
    os.makedirs("logs", exist_ok=True)
    
    logging.config.dictConfig(logging_config)


def setup_langsmith():
    """Configura LangSmith para tracing"""
    settings = get_settings()
    
    if settings.langsmith_tracing and settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_PROJECT"] = settings.app_name


def setup_sentry():
    """Configura Sentry para error tracking"""
    settings = get_settings()
    
    if settings.sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment="production" if not settings.debug else "development",
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1 if not settings.debug else 1.0,
            release=settings.app_version,
        )


def create_openai_llm(temperature: Optional[float] = None) -> "ChatOpenAI":
    """
    Crea una instancia de ChatOpenAI con la configuración centralizada
    
    Args:
        temperature: Temperatura específica, si no se proporciona usa la del config
        
    Returns:
        Instancia configurada de ChatOpenAI
    """
    from langchain_openai import ChatOpenAI
    
    settings = get_settings()
    
    return ChatOpenAI(
        model=settings.openai_model,
        temperature=temperature if temperature is not None else settings.openai_temperature,
        max_tokens=settings.openai_max_tokens,
        api_key=settings.openai_api_key
    )