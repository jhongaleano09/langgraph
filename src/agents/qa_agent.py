"""
Agente QA - Validador de Calidad
Responsable de validar la coherencia y calidad de los reportes generados
"""
import logging
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from ..utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class QAAgent:
    """
    Agente especializado en validación de calidad y coherencia de reportes
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            api_key=settings.openai_api_key
        )
        self.prompt = self._create_prompt()
    
    def _create_prompt(self) -> ChatPromptTemplate:
        """Crea el prompt para validación QA"""
        
        system_message = """
        Eres un analista de calidad experto en Business Intelligence y reportes de datos. 
        Tu tarea es evaluar la coherencia, precisión y completitud de los reportes generados 
        comparándolos con la consulta original del usuario.

        CRITERIOS DE EVALUACIÓN:

        1. COHERENCIA SEMÁNTICA (30%):
           - ¿Los datos responden exactamente lo que preguntó el usuario?
           - ¿El contexto temporal es correcto?
           - ¿Las métricas calculadas son las apropiadas?

        2. COMPLETITUD (25%):
           - ¿Se incluyen todas las dimensiones solicitadas?
           - ¿Faltan filtros o agrupaciones importantes?
           - ¿El rango de datos es apropiado?

        3. CALIDAD DE DATOS (25%):
           - ¿Los números son realistas?
           - ¿Hay outliers que requieren explicación?
           - ¿La cantidad de datos es suficiente para conclusiones?

        4. VISUALIZACIÓN (20%):
           - ¿El tipo de gráfico es apropiado para los datos?
           - ¿Se puede interpretar fácilmente?
           - ¿Los labels y título son descriptivos?

        ESCALA DE EVALUACIÓN:
        - 9-10: Excelente, aprobado sin reservas
        - 7-8: Bueno, aprobado con observaciones menores
        - 5-6: Aceptable, requiere mejoras específicas
        - 1-4: Deficiente, rechazado con feedback detallado

        FORMATO DE RESPUESTA:
        {{
            "approved": true/false,
            "overall_score": 8.5,
            "scores": {{
                "coherence": 9.0,
                "completeness": 8.0,
                "data_quality": 8.5,
                "visualization": 8.5
            }},
            "feedback": "Análisis detallado del reporte...",
            "specific_issues": [
                "Lista de problemas específicos encontrados"
            ],
            "suggestions": [
                "Sugerencias específicas para mejorar"
            ],
            "highlights": [
                "Aspectos positivos del reporte"
            ]
        }}
        """
        
        human_message = """
        CONSULTA ORIGINAL DEL USUARIO:
        "{original_query}"

        PERFIL DEL USUARIO:
        {user_profile}

        CONSULTA SQL GENERADA:
        {sql_query}

        EXPLICACIÓN DE LA CONSULTA:
        {sql_explanation}

        DATOS OBTENIDOS:
        - Número de filas: {row_count}
        - Columnas: {columns}
        - Muestra de datos:
        {data_sample}

        ESTADÍSTICAS BÁSICAS:
        {data_statistics}

        VISUALIZACIÓN:
        - Tipo de gráfico: {chart_type}
        - Título: {chart_title}
        - Justificación: {chart_reasoning}

        ITERACIÓN NÚMERO: {iteration_count}

        FEEDBACK ANTERIOR (si aplica):
        {previous_feedback}

        Evalúa este reporte completo y determina si responde adecuadamente 
        a la consulta original del usuario. Si es la iteración 3, 
        sé más permisivo pero mantén estándares de calidad básicos.
        """
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message)
        ])
    
    async def validate_report(
        self,
        original_query: str,
        sql_query: str,
        sql_explanation: str,
        data_results: List[Dict[str, Any]],
        visualization_metadata: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None,
        iteration_count: int = 1,
        previous_feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Valida la calidad y coherencia de un reporte completo
        
        Args:
            original_query: Consulta original del usuario
            sql_query: SQL generado
            sql_explanation: Explicación de la consulta
            data_results: Resultados de los datos
            visualization_metadata: Metadatos de la visualización
            user_profile: Perfil del usuario (opcional)
            iteration_count: Número de iteración actual
            previous_feedback: Feedback de iteraciones anteriores
            
        Returns:
            Dict con validación y feedback detallado
        """
        try:
            logger.info(f"Validando reporte - Iteración {iteration_count}")
            
            # 1. Preparar análisis de datos
            data_analysis = self._analyze_data_results(data_results)
            
            # 2. Preparar input para LLM
            prompt_input = {
                "original_query": original_query,
                "user_profile": user_profile or {"role": "usuario general"},
                "sql_query": sql_query,
                "sql_explanation": sql_explanation,
                "row_count": len(data_results),
                "columns": list(data_results[0].keys()) if data_results else [],
                "data_sample": data_results[:5] if data_results else [],
                "data_statistics": data_analysis["statistics"],
                "chart_type": visualization_metadata.get("chart_type", "N/A"),
                "chart_title": visualization_metadata.get("title", "N/A"),
                "chart_reasoning": visualization_metadata.get("reasoning", "N/A"),
                "iteration_count": iteration_count,
                "previous_feedback": previous_feedback or "Primera iteración"
            }
            
            # 3. Generar validación con LLM
            messages = self.prompt.format_messages(**prompt_input)
            response = await self.llm.ainvoke(messages)
            
            # 4. Parsear respuesta
            qa_result = self._parse_qa_response(response.content)
            
            # 5. Aplicar lógica de iteraciones
            qa_result = self._apply_iteration_logic(qa_result, iteration_count)
            
            # 6. Agregar metadatos adicionales
            qa_result["metadata"] = {
                "iteration_count": iteration_count,
                "data_quality_metrics": data_analysis["quality_metrics"],
                "validation_timestamp": self._get_timestamp(),
                "max_iterations_reached": iteration_count >= settings.max_iterations
            }
            
            logger.info(f"Validación completada - Aprobado: {qa_result['approved']}")
            return qa_result
            
        except Exception as e:
            logger.error(f"Error en validación QA: {str(e)}")
            return {
                "approved": False,
                "overall_score": 0.0,
                "feedback": f"Error en validación: {str(e)}",
                "specific_issues": [str(e)],
                "suggestions": ["Revisar configuración del agente QA"],
                "metadata": {"error": str(e)}
            }
    
    def _analyze_data_results(self, data_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analiza los resultados de datos para métricas de calidad"""
        
        if not data_results:
            return {
                "statistics": {},
                "quality_metrics": {
                    "has_data": False,
                    "row_count": 0,
                    "null_percentage": 0,
                    "unique_values": {}
                }
            }
        
        import pandas as pd
        df = pd.DataFrame(data_results)
        
        # Estadísticas básicas
        statistics = {}
        quality_metrics = {
            "has_data": True,
            "row_count": len(df),
            "null_percentage": (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100,
            "unique_values": {}
        }
        
        for col in df.columns:
            col_stats = {
                "dtype": str(df[col].dtype),
                "unique_count": df[col].nunique(),
                "null_count": df[col].isnull().sum(),
                "sample_values": df[col].head(3).tolist()
            }
            
            # Estadísticas numéricas
            if pd.api.types.is_numeric_dtype(df[col]):
                col_stats.update({
                    "mean": float(df[col].mean()),
                    "median": float(df[col].median()),
                    "std": float(df[col].std()),
                    "min": float(df[col].min()),
                    "max": float(df[col].max())
                })
            
            statistics[col] = col_stats
            quality_metrics["unique_values"][col] = df[col].nunique()
        
        return {
            "statistics": statistics,
            "quality_metrics": quality_metrics
        }
    
    def _parse_qa_response(self, response_content: str) -> Dict[str, Any]:
        """Parsea la respuesta del LLM de validación"""
        import json
        
        try:
            content = response_content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            result = json.loads(content.strip())
            
            # Validar campos requeridos
            required_fields = ["approved", "overall_score", "feedback"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Campo requerido faltante: {field}")
            
            # Asegurar tipos correctos
            result["approved"] = bool(result["approved"])
            result["overall_score"] = float(result["overall_score"])
            
            # Campos por defecto
            result.setdefault("specific_issues", [])
            result.setdefault("suggestions", [])
            result.setdefault("highlights", [])
            result.setdefault("scores", {})
            
            return result
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Error parseando respuesta QA, usando fallback: {str(e)}")
            return {
                "approved": False,
                "overall_score": 5.0,
                "feedback": "Error en el parsing de la validación. Requiere revisión manual.",
                "specific_issues": [f"Error de parsing: {str(e)}"],
                "suggestions": ["Revisar formato de respuesta del agente QA"],
                "highlights": []
            }
    
    def _apply_iteration_logic(
        self,
        qa_result: Dict[str, Any],
        iteration_count: int
    ) -> Dict[str, Any]:
        """Aplica lógica específica según el número de iteración"""
        
        max_iterations = getattr(settings, 'max_iterations', 3)
        
        # Si llegamos al máximo de iteraciones, ser más permisivo
        if iteration_count >= max_iterations:
            if qa_result["overall_score"] >= 5.0:  # Estándar mínimo reducido
                qa_result["approved"] = True
                qa_result["feedback"] += f"\n\n[NOTA: Aprobado al alcanzar máximo de iteraciones ({max_iterations})]"
            else:
                qa_result["feedback"] += f"\n\n[ADVERTENCIA: Máximo de iteraciones alcanzado ({max_iterations}). Reporte con calidad limitada.]"
        else:
            # Lógica normal: aprobar solo si score >= 7.0
            qa_result["approved"] = qa_result["overall_score"] >= 7.0
        
        return qa_result
    
    def _get_timestamp(self) -> str:
        """Obtiene timestamp actual"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    async def generate_improvement_suggestions(
        self,
        original_query: str,
        current_sql: str,
        issues: List[str]
    ) -> List[str]:
        """Genera sugerencias específicas de mejora"""
        
        improvement_prompt = f"""
        Basándote en estos problemas identificados en el reporte:
        
        CONSULTA ORIGINAL: {original_query}
        SQL ACTUAL: {current_sql}
        PROBLEMAS: {', '.join(issues)}
        
        Genera 3-5 sugerencias específicas y accionables para mejorar el SQL 
        y que responda mejor a la consulta original.
        """
        
        try:
            response = await self.llm.ainvoke(improvement_prompt)
            suggestions = response.content.strip().split('\n')
            return [s.strip('- ').strip() for s in suggestions if s.strip()]
        except Exception as e:
            logger.error(f"Error generando sugerencias: {str(e)}")
            return ["Revisar la consulta SQL manualmente"]