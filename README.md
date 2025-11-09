# Text-to-Report Chatbot

Sistema multiagente basado en LangGraph que permite generar reportes PDF profesionales a partir de consultas en lenguaje natural sobre una base de datos PostgreSQL.

## 🏗️ Arquitectura

El sistema implementa un workflow multiagente con tres agentes especializados:

- **Agente SQL**: Interpreta consultas naturales y genera SQL optimizado
- **Agente de Visualización**: Crea gráficos apropiados para los datos
- **Agente QA**: Valida la coherencia y calidad del reporte generado

## 🚀 Quick Start

### Prerequisitos

- Python 3.11+
- PostgreSQL 13+
- Redis 6+
- Docker y Docker Compose

### Instalación Local

1. **Clonar el repositorio:**
```bash
git clone <repo-url>
cd text-to-report-chatbot
```

2. **Instalar dependencias:**
```bash
# Usando Poetry (recomendado)
poetry install

# O usando pip
pip install -r requirements.txt
```

3. **Configurar variables de entorno:**
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

4. **Inicializar base de datos:**
```bash
poetry run alembic upgrade head
```

5. **Ejecutar el servidor:**
```bash
# Desarrollo
poetry run uvicorn src.main:app --reload

# Producción
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Deployment con Docker

```bash
docker-compose up -d
```

## 📁 Estructura del Proyecto

```
├── src/                          # Código fuente principal
│   ├── agents/                   # Agentes especializados
│   ├── database/                 # Conexiones y modelos DB
│   ├── workflows/                # LangGraph workflows
│   ├── visualization/            # Motor de gráficos
│   ├── pdf_generator/           # Generación de PDF
│   └── utils/                   # Utilidades compartidas
├── langgraph_api/               # Servidor LangGraph API
├── notebooks/                   # Jupyter notebooks para desarrollo
├── config/                      # Configuraciones
├── deployment/                  # Scripts y configs de deployment
├── templates/                   # Templates HTML para PDF
├── static/                      # Archivos estáticos
├── tests/                       # Tests unitarios e integración
└── docs/                        # Documentación
```

## 🔧 Configuración

### Variables de Entorno

Copiar `.env.example` a `.env` y configurar:

```env
# LLM Configuration
OPENAI_API_KEY=tu_openai_key
LANGSMITH_API_KEY=tu_langsmith_key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# Application
DEBUG=true
LOG_LEVEL=INFO
```

## 📊 Uso

### API Endpoints

- `POST /api/v1/query` - Procesar consulta natural
- `GET /api/v1/report/{report_id}` - Descargar PDF generado
- `GET /api/v1/health` - Health check

### Ejemplo de Consulta

```python
import httpx

response = httpx.post("http://localhost:8000/api/v1/query", 
    json={"query": "ventas del último mes por región"}
)
```

## 🧪 Testing

```bash
# Ejecutar todos los tests
poetry run pytest

# Con coverage
poetry run pytest --cov=src

# Solo tests unitarios
poetry run pytest tests/unit/

# Solo tests de integración
poetry run pytest tests/integration/
```

## 🚀 Deployment en Azure VM

### 1. Preparación de la VM

```bash
# En Azure VM
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose git nginx
sudo systemctl enable docker
sudo systemctl start docker
```

### 2. Deploy de la aplicación

```bash
# Clonar y configurar
git clone <repo-url>
cd text-to-report-chatbot
cp deployment/azure/.env.production .env

# Construir y ejecutar
sudo docker-compose -f deployment/docker-compose.prod.yml up -d
```

### 3. Configurar Nginx

```bash
sudo cp deployment/nginx/chatbot.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/chatbot.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 📈 Monitoring

- **Logs**: `docker-compose logs -f`
- **Métricas**: Prometheus en `http://vm-ip:9090`
- **Dashboard**: Grafana en `http://vm-ip:3000`
- **Tracing**: Langsmith dashboard

## 🤝 Contribución

1. Fork del repositorio
2. Crear feature branch: `git checkout -b feature/nueva-funcionalidad`
3. Commit cambios: `git commit -am 'Agregar nueva funcionalidad'`
4. Push a branch: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

## 📝 Licencia

MIT License. Ver `LICENSE` para más detalles.

## 🆘 Soporte

- **Issues**: GitHub Issues
- **Documentación**: `docs/`
- **Ejemplos**: `notebooks/`