#!/usr/bin/env python3
"""
Script de prueba para verificar la configuración de OpenAI
"""
import os
import sys

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.config import get_settings, create_openai_llm

def test_configuration():
    """Prueba la configuración de OpenAI"""
    print("🔧 Probando configuración de OpenAI...")
    
    try:
        # Cargar configuración
        settings = get_settings()
        print(f"✅ Configuración cargada exitosamente")
        print(f"   - Modelo: {settings.openai_model}")
        print(f"   - Temperatura: {settings.openai_temperature}")
        print(f"   - API Key: {settings.openai_api_key[:10]}...{settings.openai_api_key[-4:]}")
        
        # Crear instancia de LLM
        llm = create_openai_llm()
        print(f"✅ LLM creado exitosamente: {llm.model_name}")
        
        # Prueba básica
        print("\n🧪 Probando conexión con OpenAI...")
        response = llm.invoke("Responde con 'Configuración exitosa' si puedes leer este mensaje.")
        print(f"✅ Respuesta de OpenAI: {response.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en la configuración: {str(e)}")
        return False

def test_agents():
    """Prueba la inicialización de los agentes"""
    print("\n🤖 Probando inicialización de agentes...")
    
    try:
        # Importar agentes
        from src.agents.sql_agent import SQLAgent
        from src.agents.qa_agent import QAAgent
        from src.agents.visualization_agent import VisualizationAgent
        
        # Crear instancias
        sql_agent = SQLAgent()
        print(f"✅ SQL Agent: {sql_agent.llm.model_name}")
        
        qa_agent = QAAgent()
        print(f"✅ QA Agent: {qa_agent.llm.model_name}")
        
        viz_agent = VisualizationAgent()
        print(f"✅ Visualization Agent: {viz_agent.llm.model_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error inicializando agentes: {str(e)}")
        return False

def main():
    """Función principal"""
    print("🚀 Iniciando pruebas de configuración LangGraph\n")
    
    # Verificar archivo .env
    if not os.path.exists('.env'):
        print("❌ Archivo .env no encontrado. Creando uno básico...")
        return False
    
    # Ejecutar pruebas
    config_ok = test_configuration()
    agents_ok = test_agents()
    
    print("\n📊 Resumen de pruebas:")
    print(f"   - Configuración: {'✅' if config_ok else '❌'}")
    print(f"   - Agentes: {'✅' if agents_ok else '❌'}")
    
    if config_ok and agents_ok:
        print("\n🎉 ¡Todo configurado correctamente!")
        print("💡 Ahora puedes cambiar el modelo editando OPENAI_MODEL en .env")
        print("💡 Modelos disponibles: gpt-4o-mini, gpt-4o, gpt-4, gpt-3.5-turbo")
    else:
        print("\n⚠️  Hay problemas en la configuración. Revisa los errores arriba.")

if __name__ == "__main__":
    main()