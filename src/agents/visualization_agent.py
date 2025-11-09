"""
Agente de Visualización
Responsable de decidir y generar gráficos apropiados para los datos
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
import io
import base64
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from ..utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VisualizationAgent:
    """
    Agente especializado en generar visualizaciones inteligentes
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.2,
            api_key=settings.openai_api_key
        )
        self.prompt = self._create_prompt()
        
        # Configurar estilo de gráficos
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    def _create_prompt(self) -> ChatPromptTemplate:
        """Crea el prompt para análisis y selección de visualización"""
        
        system_message = """
        Eres un experto en visualización de datos y business intelligence. Tu tarea es analizar datos y decidir 
        la mejor visualización para representar la información de manera clara y efectiva.

        TIPOS DE GRÁFICOS DISPONIBLES:
        1. bar - Gráfico de barras (comparaciones categóricas)
        2. line - Gráfico de líneas (tendencias temporales)
        3. scatter - Dispersión (correlaciones)
        4. pie - Gráfico circular (proporciones)
        5. heatmap - Mapa de calor (correlaciones/matriz)
        6. histogram - Histograma (distribuciones)
        7. box - Box plot (distribuciones y outliers)
        8. area - Gráfico de área (tendencias acumuladas)

        REGLAS DE DECISIÓN:
        - Datos temporales → line, area
        - Comparaciones categóricas → bar
        - Proporciones/partes de un todo → pie
        - Correlaciones numéricas → scatter, heatmap
        - Distribuciones → histogram, box
        - Múltiples series temporales → line con múltiples líneas
        - Datos geográficos → considerar mapas (si aplicable)

        CONSIDERACIONES DE CALIDAD:
        - Máximo 20 categorías en gráficos de barras
        - Usar colores contrastantes y accesibles
        - Titles y labels descriptivos
        - Escalas apropiadas
        - Evitar 3D innecesario
        - Priorizar claridad sobre estética

        FORMATO DE RESPUESTA:
        {{
            "chart_type": "bar|line|scatter|pie|heatmap|histogram|box|area",
            "title": "Título descriptivo del gráfico",
            "x_column": "nombre_columna_x",
            "y_column": "nombre_columna_y",
            "color_column": "columna_para_color_opcional",
            "aggregation": "sum|avg|count|max|min|none",
            "reasoning": "Explicación de por qué este tipo de gráfico es apropiado",
            "chart_config": {{
                "additional_parameters": "específicos del tipo de gráfico"
            }}
        }}
        """
        
        human_message = """
        CONSULTA ORIGINAL: {original_query}
        
        DATOS A VISUALIZAR:
        - Número de filas: {row_count}
        - Columnas: {columns_info}
        - Muestra de datos:
        {data_sample}
        
        ESTADÍSTICAS BÁSICAS:
        {data_stats}
        
        Analiza estos datos y decide la mejor visualización. Considera el contexto de la consulta original.
        """
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message)
        ])
    
    async def create_visualization(
        self,
        data_results: List[Dict[str, Any]],
        original_query: str,
        sql_explanation: str
    ) -> Dict[str, Any]:
        """
        Crea una visualización inteligente de los datos
        
        Args:
            data_results: Resultados de la consulta SQL
            original_query: Consulta original del usuario
            sql_explanation: Explicación de la consulta SQL
            
        Returns:
            Dict con imagen de la visualización y metadatos
        """
        try:
            logger.info("Iniciando creación de visualización")
            
            if not data_results:
                return self._create_empty_chart("No hay datos para visualizar")
            
            # 1. Convertir a DataFrame para análisis
            df = pd.DataFrame(data_results)
            
            # 2. Analizar estructura de datos
            analysis = self._analyze_data_structure(df)
            
            # 3. Decidir tipo de gráfico con LLM
            chart_decision = await self._decide_chart_type(
                df, original_query, analysis
            )
            
            # 4. Generar visualización
            chart_bytes = await self._generate_chart(df, chart_decision)
            
            # 5. Preparar resultado
            return {
                "success": True,
                "visualization": chart_bytes,
                "chart_type": chart_decision["chart_type"],
                "title": chart_decision["title"],
                "metadata": {
                    "reasoning": chart_decision["reasoning"],
                    "columns_used": [
                        chart_decision.get("x_column"),
                        chart_decision.get("y_column"),
                        chart_decision.get("color_column")
                    ],
                    "data_rows": len(df),
                    "chart_config": chart_decision.get("chart_config", {})
                }
            }
            
        except Exception as e:
            logger.error(f"Error creando visualización: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "visualization": self._create_error_chart(str(e)),
                "chart_type": "error",
                "title": "Error en visualización",
                "metadata": {}
            }
    
    def _analyze_data_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analiza la estructura y características de los datos"""
        
        analysis = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns_info": {},
            "has_datetime": False,
            "has_numeric": False,
            "has_categorical": False
        }
        
        for col in df.columns:
            col_info = {
                "dtype": str(df[col].dtype),
                "null_count": df[col].isnull().sum(),
                "unique_count": df[col].nunique(),
                "sample_values": df[col].head(3).tolist()
            }
            
            # Detectar tipos de datos
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                col_info["data_type"] = "datetime"
                analysis["has_datetime"] = True
            elif pd.api.types.is_numeric_dtype(df[col]):
                col_info["data_type"] = "numeric"
                col_info["min_val"] = df[col].min()
                col_info["max_val"] = df[col].max()
                col_info["mean_val"] = df[col].mean()
                analysis["has_numeric"] = True
            else:
                col_info["data_type"] = "categorical"
                analysis["has_categorical"] = True
            
            analysis["columns_info"][col] = col_info
        
        return analysis
    
    async def _decide_chart_type(
        self,
        df: pd.DataFrame,
        original_query: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Usa LLM para decidir el mejor tipo de gráfico"""
        
        # Preparar información para el LLM
        columns_summary = {}
        for col, info in analysis["columns_info"].items():
            columns_summary[col] = {
                "type": info["data_type"],
                "unique_values": info["unique_count"],
                "sample": info["sample_values"]
            }
        
        # Generar estadísticas básicas
        stats = {}
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                stats[col] = {
                    "mean": float(df[col].mean()),
                    "std": float(df[col].std()),
                    "min": float(df[col].min()),
                    "max": float(df[col].max())
                }
        
        prompt_input = {
            "original_query": original_query,
            "row_count": len(df),
            "columns_info": columns_summary,
            "data_sample": df.head(5).to_dict('records'),
            "data_stats": stats
        }
        
        messages = self.prompt.format_messages(**prompt_input)
        response = await self.llm.ainvoke(messages)
        
        return self._parse_chart_decision(response.content)
    
    def _parse_chart_decision(self, response_content: str) -> Dict[str, Any]:
        """Parsea la decisión del LLM sobre el tipo de gráfico"""
        import json
        
        try:
            content = response_content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            decision = json.loads(content.strip())
            
            # Validar campos requeridos
            required_fields = ["chart_type", "title"]
            for field in required_fields:
                if field not in decision:
                    raise ValueError(f"Campo requerido faltante: {field}")
            
            return decision
            
        except json.JSONDecodeError:
            # Fallback si el parsing falla
            return {
                "chart_type": "bar",
                "title": "Visualización de Datos",
                "reasoning": "Fallback por error de parsing",
                "chart_config": {}
            }
    
    async def _generate_chart(
        self,
        df: pd.DataFrame,
        decision: Dict[str, Any]
    ) -> bytes:
        """Genera el gráfico según la decisión"""
        
        chart_type = decision["chart_type"]
        title = decision["title"]
        
        if chart_type == "bar":
            return self._create_bar_chart(df, decision)
        elif chart_type == "line":
            return self._create_line_chart(df, decision)
        elif chart_type == "scatter":
            return self._create_scatter_chart(df, decision)
        elif chart_type == "pie":
            return self._create_pie_chart(df, decision)
        elif chart_type == "heatmap":
            return self._create_heatmap(df, decision)
        elif chart_type == "histogram":
            return self._create_histogram(df, decision)
        else:
            # Default: bar chart
            return self._create_bar_chart(df, decision)
    
    def _create_bar_chart(self, df: pd.DataFrame, decision: Dict[str, Any]) -> bytes:
        """Crea gráfico de barras con Plotly"""
        
        x_col = decision.get("x_column", df.columns[0])
        y_col = decision.get("y_column", df.columns[1] if len(df.columns) > 1 else df.columns[0])
        
        fig = px.bar(
            df,
            x=x_col,
            y=y_col,
            title=decision["title"],
            color=decision.get("color_column"),
            template="plotly_white"
        )
        
        fig.update_layout(
            font=dict(size=12),
            title_font_size=16,
            height=500,
            margin=dict(t=50, b=50, l=50, r=50)
        )
        
        return self._fig_to_bytes(fig)
    
    def _create_line_chart(self, df: pd.DataFrame, decision: Dict[str, Any]) -> bytes:
        """Crea gráfico de líneas con Plotly"""
        
        x_col = decision.get("x_column", df.columns[0])
        y_col = decision.get("y_column", df.columns[1] if len(df.columns) > 1 else df.columns[0])
        
        fig = px.line(
            df,
            x=x_col,
            y=y_col,
            title=decision["title"],
            color=decision.get("color_column"),
            template="plotly_white"
        )
        
        fig.update_layout(
            font=dict(size=12),
            title_font_size=16,
            height=500
        )
        
        return self._fig_to_bytes(fig)
    
    def _create_scatter_chart(self, df: pd.DataFrame, decision: Dict[str, Any]) -> bytes:
        """Crea gráfico de dispersión"""
        
        x_col = decision.get("x_column", df.columns[0])
        y_col = decision.get("y_column", df.columns[1] if len(df.columns) > 1 else df.columns[0])
        
        fig = px.scatter(
            df,
            x=x_col,
            y=y_col,
            title=decision["title"],
            color=decision.get("color_column"),
            template="plotly_white"
        )
        
        fig.update_layout(
            font=dict(size=12),
            title_font_size=16,
            height=500
        )
        
        return self._fig_to_bytes(fig)
    
    def _create_pie_chart(self, df: pd.DataFrame, decision: Dict[str, Any]) -> bytes:
        """Crea gráfico circular"""
        
        values_col = decision.get("y_column", df.columns[1] if len(df.columns) > 1 else df.columns[0])
        names_col = decision.get("x_column", df.columns[0])
        
        fig = px.pie(
            df,
            values=values_col,
            names=names_col,
            title=decision["title"]
        )
        
        fig.update_layout(
            font=dict(size=12),
            title_font_size=16,
            height=500
        )
        
        return self._fig_to_bytes(fig)
    
    def _create_heatmap(self, df: pd.DataFrame, decision: Dict[str, Any]) -> bytes:
        """Crea mapa de calor"""
        
        # Seleccionar solo columnas numéricas para correlación
        numeric_df = df.select_dtypes(include=['number'])
        
        if numeric_df.empty:
            return self._create_empty_chart("No hay datos numéricos para mapa de calor")
        
        corr_matrix = numeric_df.corr()
        
        fig = px.imshow(
            corr_matrix,
            title=decision["title"],
            color_continuous_scale="RdBu_r",
            aspect="auto"
        )
        
        fig.update_layout(
            font=dict(size=12),
            title_font_size=16,
            height=500
        )
        
        return self._fig_to_bytes(fig)
    
    def _create_histogram(self, df: pd.DataFrame, decision: Dict[str, Any]) -> bytes:
        """Crea histograma"""
        
        x_col = decision.get("x_column", df.columns[0])
        
        fig = px.histogram(
            df,
            x=x_col,
            title=decision["title"],
            template="plotly_white"
        )
        
        fig.update_layout(
            font=dict(size=12),
            title_font_size=16,
            height=500
        )
        
        return self._fig_to_bytes(fig)
    
    def _fig_to_bytes(self, fig) -> bytes:
        """Convierte figura de Plotly a bytes"""
        
        img_bytes = fig.to_image(format="png", engine="auto")
        return img_bytes
    
    def _create_empty_chart(self, message: str) -> bytes:
        """Crea un gráfico vacío con mensaje"""
        
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20)
        )
        fig.update_layout(
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=400
        )
        
        return self._fig_to_bytes(fig)
    
    def _create_error_chart(self, error_message: str) -> bytes:
        """Crea un gráfico de error"""
        
        return self._create_empty_chart(f"Error: {error_message}")