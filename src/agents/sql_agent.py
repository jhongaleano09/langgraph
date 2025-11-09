"""
Agente SQL - Text-to-SQL especializado
Responsable de interpretar consultas naturales y generar SQL optimizado
"""
import logging
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage
from sqlalchemy.exc import SQLAlchemyError

from ..database.manager import DatabaseManager
from ..database.metadata_manager import MetadataManager
from ..utils.sql_validator import SQLValidator
from ..utils.config import get_settings, create_openai_llm

logger = logging.getLogger(__name__)
settings = get_settings()


class SQLAgent:
    """
    Agente especializado en generación de SQL a partir de consultas naturales
    """
    
    def __init__(self):
        self.llm = create_openai_llm()
        self.db_manager = DatabaseManager()
        self.metadata_manager = MetadataManager()
        self.sql_validator = SQLValidator()
        self.prompt = self._create_prompt()
    
    def _create_prompt(self) -> ChatPromptTemplate:
        """Crea el prompt optimizado para Text-to-SQL"""
        
        system_message = """
        Eres un experto analista SQL especializado en convertir consultas en lenguaje natural a SQL preciso y optimizado.

        CONTEXTO DE BASE DE DATOS:
        {database_schema}
        
        DICCIONARIO DE DATOS:
        {data_dictionary}
        
        RELACIONES IMPORTANTES:
        {relationships}

        REGLAS ESTRICTAS:
        1. SOLO generar consultas SELECT
        2. Usar ÚNICAMENTE las tablas y columnas del esquema proporcionado
        3. Aplicar filtros de seguridad para evitar consultas que retornen demasiados datos
        4. Usar JOINs apropiados basándose en las relaciones FK
        5. Incluir LIMIT cuando sea apropiado para performance
        6. Usar funciones de agregación cuando la consulta lo requiera
        7. Manejar fechas correctamente según el tipo de datos
        8. Validar que los nombres de columnas y tablas existan

        EJEMPLOS DE CONSULTAS COMUNES:
        {few_shot_examples}

        FORMATO DE RESPUESTA:
        Responde con un JSON válido que contenga:
        {{
            "sql_query": "SELECT ... FROM ... WHERE ...",
            "explanation": "Explicación de la consulta en español",
            "tables_used": ["tabla1", "tabla2"],
            "estimated_rows": 1000,
            "confidence_score": 0.95
        }}
        """
        
        human_message = """
        Consulta del usuario: {user_query}
        
        Contexto adicional: {additional_context}
        
        Feedback de iteración anterior (si aplica): {qa_feedback}
        
        Genera una consulta SQL precisa y optimizada.
        """
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message)
        ])
    
    async def process_query(
        self, 
        user_query: str,
        additional_context: Optional[Dict[str, Any]] = None,
        qa_feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Procesa una consulta natural y genera SQL
        
        Args:
            user_query: Consulta en lenguaje natural
            additional_context: Contexto adicional del usuario
            qa_feedback: Feedback del agente QA para mejoras
            
        Returns:
            Dict con SQL generado, datos y metadatos
        """
        try:
            logger.info(f"Procesando consulta: {user_query}")
            
            # 1. Obtener metadatos de la base de datos
            schema_info = await self.metadata_manager.get_full_schema()
            data_dict = await self.metadata_manager.get_data_dictionary()
            relationships = await self.metadata_manager.get_relationships()
            examples = await self.metadata_manager.get_few_shot_examples()
            
            # 2. Preparar prompt
            prompt_input = {
                "user_query": user_query,
                "database_schema": schema_info,
                "data_dictionary": data_dict,
                "relationships": relationships,
                "few_shot_examples": examples,
                "additional_context": additional_context or {},
                "qa_feedback": qa_feedback or "No hay feedback previo"
            }
            
            # 3. Generar SQL con LLM
            messages = self.prompt.format_messages(**prompt_input)
            response = await self.llm.ainvoke(messages)
            
            # 4. Parsear respuesta
            sql_result = self._parse_llm_response(response.content)
            
            # 5. Validar SQL
            validation_result = await self.sql_validator.validate_sql(
                sql_result["sql_query"]
            )
            
            if not validation_result["valid"]:
                raise ValueError(f"SQL inválido: {validation_result['errors']}")
            
            # 6. Ejecutar consulta
            data_results = await self.db_manager.execute_query(
                sql_result["sql_query"]
            )
            
            # 7. Preparar resultado final
            return {
                "success": True,
                "sql_query": sql_result["sql_query"],
                "explanation": sql_result["explanation"],
                "data_results": data_results,
                "metadata": {
                    "tables_used": sql_result["tables_used"],
                    "row_count": len(data_results),
                    "estimated_rows": sql_result.get("estimated_rows", 0),
                    "confidence_score": sql_result.get("confidence_score", 0.0),
                    "execution_time": 0  # Se calculará en el manager
                }
            }
            
        except Exception as e:
            logger.error(f"Error procesando consulta SQL: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "sql_query": None,
                "data_results": [],
                "metadata": {}
            }
    
    def _parse_llm_response(self, response_content: str) -> Dict[str, Any]:
        """Parsea la respuesta JSON del LLM"""
        import json
        
        try:
            # Limpiar respuesta si tiene markdown
            content = response_content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            result = json.loads(content.strip())
            
            # Validar campos requeridos
            required_fields = ["sql_query", "explanation", "tables_used"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Campo requerido faltante: {field}")
            
            return result
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parseando respuesta JSON: {str(e)}")
    
    async def refine_query(
        self,
        original_query: str,
        current_sql: str,
        qa_feedback: str,
        execution_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Refina una consulta SQL basándose en feedback del QA
        """
        refinement_context = {
            "original_query": original_query,
            "current_sql": current_sql,
            "qa_feedback": qa_feedback,
            "current_results_sample": execution_results[:5] if execution_results else [],
            "result_count": len(execution_results)
        }
        
        return await self.process_query(
            user_query=original_query,
            additional_context=refinement_context,
            qa_feedback=qa_feedback
        )


# Función de ayuda para crear instancias del agente
def create_sql_agent() -> SQLAgent:
    """
    Crea una instancia del SQLAgent
    
    Returns:
        SQLAgent: Instancia configurada del agente SQL
    """
    return SQLAgent()