"""
PDF Generator
Motor de generación de reportes PDF usando WeasyPrint
"""
import logging
import base64
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PDFGenerator:
    """
    Generador de PDFs profesionales para reportes
    """
    
    def __init__(self):
        self.settings = get_settings()
        
        # Configurar Jinja2
        template_dir = Path(self.settings.pdf_template_dir)
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # CSS base para styling
        self.base_css = """
        @page {
            size: A4;
            margin: 1in;
            @bottom-center {
                content: "Página " counter(page) " de " counter(pages);
                font-size: 10px;
                color: #666;
            }
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
        }
        
        .header {
            border-bottom: 2px solid #3498db;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        .header h1 {
            color: #2c3e50;
            font-size: 24px;
            margin: 0;
        }
        
        .metadata {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 25px;
        }
        
        .metadata table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .metadata td {
            padding: 5px 10px;
            border-bottom: 1px solid #dee2e6;
        }
        
        .metadata .label {
            font-weight: bold;
            width: 150px;
            color: #495057;
        }
        
        .section {
            margin-bottom: 30px;
            page-break-inside: avoid;
        }
        
        .section h2 {
            color: #2c3e50;
            font-size: 18px;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        
        .query-box {
            background-color: #f1f2f6;
            border-left: 4px solid #3498db;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            margin-bottom: 20px;
            border-radius: 0 5px 5px 0;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            font-size: 12px;
        }
        
        .data-table th {
            background-color: #3498db;
            color: white;
            padding: 12px 8px;
            text-align: left;
            font-weight: bold;
        }
        
        .data-table td {
            padding: 8px;
            border-bottom: 1px solid #dee2e6;
        }
        
        .data-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        .chart-container {
            text-align: center;
            margin: 20px 0;
            page-break-inside: avoid;
        }
        
        .chart-container img {
            max-width: 100%;
            height: auto;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .insights {
            background-color: #e8f5e8;
            border-left: 4px solid #27ae60;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 5px 5px 0;
        }
        
        .insights h3 {
            color: #27ae60;
            margin-top: 0;
        }
        
        .highlights {
            list-style-type: none;
            padding: 0;
        }
        
        .highlights li {
            padding: 8px 0;
            border-bottom: 1px solid #d5e7d5;
        }
        
        .highlights li:before {
            content: "✓ ";
            color: #27ae60;
            font-weight: bold;
        }
        
        .watermark {
            position: fixed;
            bottom: 50px;
            right: 50px;
            font-size: 10px;
            color: #95a5a6;
            font-style: italic;
        }
        
        .warning {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
            color: #856404;
        }
        
        .warning h4 {
            margin-top: 0;
            color: #d35400;
        }
        
        @media print {
            .section {
                page-break-inside: avoid;
            }
            
            .chart-container {
                page-break-inside: avoid;
            }
        }
        """
    
    async def generate_report(
        self,
        original_query: str,
        sql_query: str,
        sql_explanation: str,
        data_results: List[Dict[str, Any]],
        visualization_image: bytes,
        chart_metadata: Dict[str, Any],
        qa_validation: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Genera un reporte PDF completo
        
        Args:
            original_query: Consulta original del usuario
            sql_query: SQL generado
            sql_explanation: Explicación de la consulta
            data_results: Datos obtenidos
            visualization_image: Imagen de la visualización
            chart_metadata: Metadatos del gráfico
            qa_validation: Resultado de validación QA
            user_profile: Perfil del usuario
            
        Returns:
            Bytes del PDF generado
        """
        try:
            logger.info("Generando reporte PDF")
            
            # 1. Preparar datos para el template
            report_data = {
                'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                'original_query': original_query,
                'sql_query': sql_query,
                'sql_explanation': sql_explanation,
                'data_results': data_results[:100],  # Limitar datos mostrados
                'total_rows': len(data_results),
                'chart_metadata': chart_metadata,
                'qa_validation': qa_validation,
                'user_profile': user_profile or {'name': 'Usuario'},
                'chart_image_b64': base64.b64encode(visualization_image).decode('utf-8'),
                'insights': await self._generate_insights(data_results, original_query),
                'data_summary': self._generate_data_summary(data_results),
                'chart_title': chart_metadata.get('title', 'Visualización de Datos'),
                'qa_score': qa_validation.get('overall_score', 0.0),
                'qa_approved': qa_validation.get('approved', False)
            }
            
            # 2. Renderizar HTML
            html_content = await self._render_template('report_template.html', report_data)
            
            # 3. Generar PDF
            pdf_bytes = self._html_to_pdf(html_content)
            
            logger.info("Reporte PDF generado exitosamente")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Error generando PDF: {str(e)}")
            raise PDFGenerationError(f"Error generando reporte PDF: {str(e)}")
    
    async def _render_template(
        self, 
        template_name: str, 
        data: Dict[str, Any]
    ) -> str:
        """Renderiza template HTML con datos"""
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**data)
        except Exception as e:
            logger.error(f"Error renderizando template: {str(e)}")
            # Fallback a template básico
            return self._create_basic_template(data)
    
    def _create_basic_template(self, data: Dict[str, Any]) -> str:
        """Crea un template HTML básico si el template principal falla"""
        
        # Crear tabla de datos
        data_table = ""
        if data['data_results']:
            headers = list(data['data_results'][0].keys())
            data_table = "<table class='data-table'><thead><tr>"
            for header in headers:
                data_table += f"<th>{header}</th>"
            data_table += "</tr></thead><tbody>"
            
            for row in data['data_results'][:20]:  # Limitar a 20 filas
                data_table += "<tr>"
                for header in headers:
                    value = row.get(header, '')
                    data_table += f"<td>{value}</td>"
                data_table += "</tr>"
            data_table += "</tbody></table>"
        
        # Crear insights
        insights_html = ""
        if data.get('insights'):
            insights_html = "<ul class='highlights'>"
            for insight in data['insights'][:5]:
                insights_html += f"<li>{insight}</li>"
            insights_html += "</ul>"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Reporte de Datos</title>
            <style>{self.base_css}</style>
        </head>
        <body>
            <div class="header">
                <h1>Reporte de Análisis de Datos</h1>
                <p>Generado el {data['timestamp']}</p>
            </div>
            
            <div class="metadata">
                <table>
                    <tr><td class="label">Consulta Original:</td><td>{data['original_query']}</td></tr>
                    <tr><td class="label">Total de Registros:</td><td>{data['total_rows']}</td></tr>
                    <tr><td class="label">Calificación QA:</td><td>{data['qa_score']:.1f}/10</td></tr>
                    <tr><td class="label">Estado:</td><td>{'Aprobado' if data['qa_approved'] else 'Requiere revisión'}</td></tr>
                </table>
            </div>
            
            <div class="section">
                <h2>Consulta SQL Generada</h2>
                <div class="query-box">{data['sql_query']}</div>
                <p><strong>Explicación:</strong> {data['sql_explanation']}</p>
            </div>
            
            <div class="section">
                <h2>Visualización</h2>
                <div class="chart-container">
                    <img src="data:image/png;base64,{data['chart_image_b64']}" alt="{data['chart_title']}">
                    <p><em>{data['chart_title']}</em></p>
                </div>
            </div>
            
            <div class="section">
                <h2>Datos</h2>
                {data_table}
                {f"<p><em>Mostrando primeras 20 filas de {data['total_rows']} total</em></p>" if data['total_rows'] > 20 else ""}
            </div>
            
            {f'''
            <div class="insights">
                <h3>Insights Destacados</h3>
                {insights_html}
            </div>
            ''' if insights_html else ''}
            
            <div class="warning">
                <h4>⚠️ Aviso Importante</h4>
                <p>Este reporte fue generado automáticamente por inteligencia artificial. 
                Los datos y análisis deben ser validados por un analista humano antes de tomar decisiones críticas.</p>
            </div>
            
            <div class="watermark">
                Generado por IA - {data['timestamp']} - Validación requerida
            </div>
        </body>
        </html>
        """
    
    def _html_to_pdf(self, html_content: str) -> bytes:
        """Convierte HTML a PDF usando WeasyPrint"""
        try:
            # Crear CSS object
            css = CSS(string=self.base_css)
            
            # Generar PDF
            html = HTML(string=html_content, base_url=str(Path(self.settings.pdf_template_dir)))
            pdf_bytes = html.write_pdf(stylesheets=[css])
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Error convirtiendo HTML a PDF: {str(e)}")
            raise PDFGenerationError(f"Error en conversión HTML->PDF: {str(e)}")
    
    async def _generate_insights(
        self, 
        data_results: List[Dict[str, Any]], 
        original_query: str
    ) -> List[str]:
        """Genera insights automáticos sobre los datos"""
        insights = []
        
        try:
            if not data_results:
                return ["No hay datos para analizar"]
            
            # Insights básicos sobre cantidad de datos
            row_count = len(data_results)
            if row_count == 1:
                insights.append("Se encontró 1 registro que coincide con los criterios")
            else:
                insights.append(f"Se encontraron {row_count:,} registros en total")
            
            # Análisis de columnas numéricas
            if data_results:
                sample_row = data_results[0]
                numeric_columns = []
                
                for col, value in sample_row.items():
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        numeric_columns.append(col)
                
                for col in numeric_columns[:3]:  # Máximo 3 columnas
                    values = [row.get(col, 0) for row in data_results if row.get(col) is not None]
                    if values:
                        avg_val = sum(values) / len(values)
                        max_val = max(values)
                        min_val = min(values)
                        
                        insights.append(f"{col}: promedio {avg_val:.2f}, rango {min_val} - {max_val}")
            
            # Insight sobre fechas si se detectan
            date_keywords = ['fecha', 'date', 'time', 'timestamp']
            if any(keyword in original_query.lower() for keyword in date_keywords):
                insights.append("Análisis temporal detectado - considere tendencias estacionales")
            
            # Insight sobre comparaciones
            comparison_keywords = ['comparar', 'vs', 'contra', 'diferencia']
            if any(keyword in original_query.lower() for keyword in comparison_keywords):
                insights.append("Análisis comparativo realizado - revise las diferencias significativas")
            
            return insights[:5]  # Máximo 5 insights
            
        except Exception as e:
            logger.error(f"Error generando insights: {str(e)}")
            return ["Error generando insights automáticos"]
    
    def _generate_data_summary(self, data_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Genera resumen estadístico de los datos"""
        if not data_results:
            return {"error": "No hay datos para resumir"}
        
        try:
            sample_row = data_results[0]
            summary = {
                "total_rows": len(data_results),
                "columns": list(sample_row.keys()),
                "column_count": len(sample_row.keys()),
                "numeric_columns": [],
                "text_columns": [],
                "date_columns": []
            }
            
            # Clasificar columnas por tipo
            for col in sample_row.keys():
                sample_values = [row.get(col) for row in data_results[:10] if row.get(col) is not None]
                
                if sample_values:
                    first_val = sample_values[0]
                    if isinstance(first_val, (int, float)) and not isinstance(first_val, bool):
                        summary["numeric_columns"].append(col)
                    elif isinstance(first_val, str):
                        # Detectar si podría ser fecha
                        if any(date_indicator in col.lower() for date_indicator in ['fecha', 'date', 'time']):
                            summary["date_columns"].append(col)
                        else:
                            summary["text_columns"].append(col)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generando resumen de datos: {str(e)}")
            return {"error": f"Error en resumen: {str(e)}"}


class PDFGenerationError(Exception):
    """Excepción para errores en generación de PDF"""
    pass