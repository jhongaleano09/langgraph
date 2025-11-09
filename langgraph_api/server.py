"""
LangGraph API Server Configuration
Servidor principal que orquesta el workflow multiagente
"""
import os
import uvicorn
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresCheckpoint
from typing import TypedDict, Optional, List, Dict, Any
from src.workflows.report_workflow import ReportWorkflow
from src.utils.config import get_settings

settings = get_settings()

class ReportState(TypedDict):
    """Estado del workflow de generación de reportes"""
    # Input inicial
    query: str
    user_profile: Optional[Dict[str, Any]]
    
    # Procesamiento SQL
    sql_query: Optional[str]
    data_results: Optional[List[Dict[str, Any]]]
    
    # Visualización
    visualization: Optional[bytes]
    chart_type: Optional[str]
    
    # QA y feedback
    qa_feedback: Optional[str]
    qa_approved: bool
    qa_score: Optional[float]
    
    # Control de iteraciones
    iteration_count: int
    max_iterations: int
    
    # Output final
    final_pdf: Optional[bytes]
    report_id: Optional[str]
    
    # Metadata
    timestamp: Optional[str]
    execution_time: Optional[float]
    errors: Optional[List[str]]


def create_workflow_graph() -> StateGraph:
    """Crea el grafo del workflow multiagente"""
    workflow = ReportWorkflow()
    
    # Crear el grafo
    graph = StateGraph(ReportState)
    
    # Agregar nodos
    graph.add_node("sql_agent", workflow.sql_agent_node)
    graph.add_node("visualization_agent", workflow.visualization_agent_node)
    graph.add_node("qa_agent", workflow.qa_agent_node)
    graph.add_node("pdf_generator", workflow.pdf_generator_node)
    
    # Configurar flujo
    graph.set_entry_point("sql_agent")
    
    # SQL Agent -> Visualization Agent
    graph.add_edge("sql_agent", "visualization_agent")
    
    # Visualization Agent -> QA Agent
    graph.add_edge("visualization_agent", "qa_agent")
    
    # QA Agent -> Conditional routing
    graph.add_conditional_edges(
        "qa_agent",
        workflow.qa_routing_function,
        {
            "approved": "pdf_generator",
            "rejected": "sql_agent",
            "max_iterations_reached": "pdf_generator"
        }
    )
    
    # PDF Generator -> END
    graph.add_edge("pdf_generator", END)
    
    return graph


def create_app():
    """Crea la aplicación LangGraph API"""
    
    # Configurar checkpoint para persistencia
    checkpoint = PostgresCheckpoint.from_conn_string(
        settings.database_url
    )
    
    # Crear workflow
    workflow_graph = create_workflow_graph()
    
    # Compilar con checkpoint
    app = workflow_graph.compile(
        checkpointer=checkpoint,
        interrupt_before=None,  # No interrupciones automáticas
        interrupt_after=None
    )
    
    return app


# Configuración del servidor
def main():
    """Función principal para ejecutar el servidor"""
    app = create_app()
    
    # Configurar servidor
    uvicorn.run(
        app,
        host=settings.langgraph_api_host,
        port=settings.langgraph_api_port,
        log_level=settings.log_level.lower(),
        reload=settings.debug
    )


if __name__ == "__main__":
    main()