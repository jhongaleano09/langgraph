# Configuración de OpenAI para LangGraph

## 🔐 Configuración de API Key

La API Key de OpenAI está configurada en el archivo `.env`:

```bash
OPENAI_API_KEY=your-openai-api-key-here
```

## 🤖 Configuración del Modelo

### Modelo Actual
- **Modelo por defecto**: `gpt-4o-mini` (económico para pruebas)
- **Temperatura**: `0.1` (respuestas consistentes)

### Cambio de Modelo
Para cambiar el modelo, edita el archivo `.env`:

```bash
# Modelos disponibles:
OPENAI_MODEL=gpt-4o-mini     # Más económico, bueno para pruebas
OPENAI_MODEL=gpt-4o          # Equilibrio precio/rendimiento
OPENAI_MODEL=gpt-4           # Máximo rendimiento
OPENAI_MODEL=gpt-3.5-turbo   # Más rápido y económico
```

## 🏗️ Arquitectura de Configuración

### Configuración Centralizada
Todos los agentes usan la función `create_openai_llm()` desde `src/utils/config.py`:

```python
from src.utils.config import create_openai_llm

# Usar configuración por defecto
llm = create_openai_llm()

# Usar temperatura específica
llm = create_openai_llm(temperature=0.2)
```

### Agentes Configurados
1. **SQL Agent** (`src/agents/sql_agent.py`)
   - Modelo: Configuración global
   - Temperatura: Configuración global (0.1)

2. **QA Agent** (`src/agents/qa_agent.py`)
   - Modelo: Configuración global
   - Temperatura: Configuración global (0.1)

3. **Visualization Agent** (`src/agents/visualization_agent.py`)
   - Modelo: Configuración global
   - Temperatura: 0.2 (específica para creatividad en visualización)

## 🧪 Pruebas

### Ejecutar prueba de configuración:
```bash
python test_config.py
```

Esta prueba verificará:
- ✅ Carga de configuración desde `.env`
- ✅ Creación de instancias de LLM
- ✅ Conexión con OpenAI
- ✅ Inicialización de todos los agentes

## 📝 Variables de Entorno Disponibles

```bash
# OpenAI
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.1
OPENAI_MAX_TOKENS=null  # null para sin límite

# Aplicación
APP_NAME=Text-to-Report Chatbot
DEBUG=true

# Base de datos
DATABASE_URL=postgresql://user:password@localhost/dbname
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password

# Seguridad
SECRET_KEY=your-secret-key-here
```

## 🔄 Cambio Rápido de Modelo

Para cambiar entre modelos rápidamente:

1. **Para desarrollo/pruebas**:
   ```bash
   OPENAI_MODEL=gpt-4o-mini
   ```

2. **Para producción**:
   ```bash
   OPENAI_MODEL=gpt-4o
   ```

3. **Para máximo rendimiento**:
   ```bash
   OPENAI_MODEL=gpt-4
   ```

Los cambios se aplican automáticamente al reiniciar la aplicación. No necesitas modificar código, solo el archivo `.env`.

## 💡 Recomendaciones

- **Desarrollo**: Usa `gpt-4o-mini` para reducir costos
- **Testing**: Usa `gpt-4o-mini` o `gpt-3.5-turbo`
- **Producción**: Usa `gpt-4o` para mejor calidad
- **Casos críticos**: Usa `gpt-4` para máxima precisión

## 🔒 Seguridad

- ✅ API Key configurada en variables de entorno
- ✅ Archivo `.env` incluido en `.gitignore` (agregar si no existe)
- ⚠️ Nunca commitees API Keys al repositorio
- ⚠️ Usa diferentes API Keys para desarrollo/producción