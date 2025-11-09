"""
Metadata Manager
Gestiona metadatos de la base de datos para inyección de contexto en LLMs
"""
import logging
from typing import Dict, List, Any, Optional
import json
from datetime import datetime, timedelta
from ..database.manager import get_database_manager, DatabaseManager
from ..utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MetadataManager:
    """
    Administra metadatos de la base de datos y contexto para LLMs
    """
    
    def __init__(self):
        self.db_manager: DatabaseManager = get_database_manager()
        self._cache = {}
        self._cache_ttl = timedelta(hours=1)  # Cache por 1 hora
        self._last_update = {}
    
    async def get_full_schema(self) -> str:
        """
        Obtiene el DDL completo de la base de datos formateado para LLM
        
        Returns:
            String con DDL formateado
        """
        cache_key = "full_schema"
        
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            logger.info("Generating full database schema")
            
            tables = await self.db_manager.get_table_names()
            schema_parts = []
            
            for table_name in tables:
                table_info = await self.db_manager.get_table_info(table_name)
                ddl = self._generate_table_ddl(table_info)
                schema_parts.append(ddl)
            
            full_schema = "\n\n".join(schema_parts)
            
            # Cachear resultado
            self._cache[cache_key] = full_schema
            self._last_update[cache_key] = datetime.now()
            
            logger.info(f"Schema generated for {len(tables)} tables")
            return full_schema
            
        except Exception as e:
            logger.error(f"Error generating schema: {str(e)}")
            return "-- Error generando esquema de base de datos"
    
    def _generate_table_ddl(self, table_info: Dict[str, Any]) -> str:
        """
        Genera DDL para una tabla específica
        
        Args:
            table_info: Información de la tabla
            
        Returns:
            String con DDL de la tabla
        """
        table_name = table_info["table_name"]
        columns = table_info["columns"]
        primary_keys = table_info["primary_keys"]
        foreign_keys = table_info["foreign_keys"]
        
        ddl_parts = [f"CREATE TABLE {table_name} ("]
        
        # Definir columnas
        column_definitions = []
        for col in columns:
            col_def = f"    {col['column_name']} {col['data_type']}"
            
            # Agregar longitud si aplica
            if col['character_maximum_length']:
                col_def += f"({col['character_maximum_length']})"
            elif col['numeric_precision']:
                if col['numeric_scale']:
                    col_def += f"({col['numeric_precision']},{col['numeric_scale']})"
                else:
                    col_def += f"({col['numeric_precision']})"
            
            # Nullable
            if col['is_nullable'] == 'NO':
                col_def += " NOT NULL"
            
            # Default
            if col['column_default']:
                col_def += f" DEFAULT {col['column_default']}"
            
            column_definitions.append(col_def)
        
        ddl_parts.extend(column_definitions)
        
        # Primary keys
        if primary_keys:
            pk_def = f"    PRIMARY KEY ({', '.join(primary_keys)})"
            ddl_parts.append(pk_def)
        
        # Foreign keys
        for fk in foreign_keys:
            fk_def = f"    FOREIGN KEY ({fk['column_name']}) REFERENCES {fk['foreign_table_name']}({fk['foreign_column_name']})"
            ddl_parts.append(fk_def)
        
        ddl_parts.append(");")
        
        # Comentarios sobre la tabla
        comment_parts = [
            f"\n-- Tabla: {table_name}",
            f"-- Columnas: {len(columns)}",
            f"-- Claves primarias: {', '.join(primary_keys) if primary_keys else 'Ninguna'}",
            f"-- Claves foráneas: {len(foreign_keys)}"
        ]
        
        return "\n".join(comment_parts) + "\n" + ",\n".join(ddl_parts[0:1] + ddl_parts[1:-1]) + "\n" + ddl_parts[-1]
    
    async def get_data_dictionary(self) -> str:
        """
        Obtiene el diccionario de datos formateado para LLM
        
        Returns:
            String con diccionario de datos
        """
        cache_key = "data_dictionary"
        
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            logger.info("Generating data dictionary")
            
            tables = await self.db_manager.get_table_names()
            dictionary_parts = []
            
            for table_name in tables:
                table_info = await self.db_manager.get_table_info(table_name)
                sample_data = await self.db_manager.get_sample_data(table_name, 3)
                
                table_dict = self._generate_table_dictionary(table_info, sample_data)
                dictionary_parts.append(table_dict)
            
            full_dictionary = "\n\n".join(dictionary_parts)
            
            # Cachear resultado
            self._cache[cache_key] = full_dictionary
            self._last_update[cache_key] = datetime.now()
            
            logger.info(f"Data dictionary generated for {len(tables)} tables")
            return full_dictionary
            
        except Exception as e:
            logger.error(f"Error generating data dictionary: {str(e)}")
            return "-- Error generando diccionario de datos"
    
    def _generate_table_dictionary(
        self, 
        table_info: Dict[str, Any], 
        sample_data: List[Dict[str, Any]]
    ) -> str:
        """
        Genera entrada del diccionario para una tabla
        """
        table_name = table_info["table_name"]
        columns = table_info["columns"]
        
        parts = [f"TABLA: {table_name}"]
        parts.append("=" * (len(table_name) + 7))
        
        # Información de columnas
        for col in columns:
            col_name = col['column_name']
            data_type = col['data_type']
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            
            # Obtener valores de muestra
            sample_values = []
            if sample_data:
                for row in sample_data:
                    if col_name in row and row[col_name] is not None:
                        sample_values.append(str(row[col_name]))
                
                if sample_values:
                    sample_str = f" | Ejemplos: {', '.join(sample_values[:3])}"
                else:
                    sample_str = " | Ejemplos: (sin datos)"
            else:
                sample_str = ""
            
            col_desc = f"  - {col_name}: {data_type} ({nullable}){sample_str}"
            parts.append(col_desc)
        
        # Información adicional
        if table_info["primary_keys"]:
            parts.append(f"\nClaves Primarias: {', '.join(table_info['primary_keys'])}")
        
        if table_info["foreign_keys"]:
            fk_info = []
            for fk in table_info["foreign_keys"]:
                fk_info.append(f"{fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']}")
            parts.append(f"Claves Foráneas: {', '.join(fk_info)}")
        
        return "\n".join(parts)
    
    async def get_relationships(self) -> str:
        """
        Obtiene información de relaciones entre tablas
        
        Returns:
            String con relaciones formateadas
        """
        cache_key = "relationships"
        
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            logger.info("Generating table relationships")
            
            # Query para obtener todas las relaciones FK
            fk_query = """
                SELECT 
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    tc.constraint_name
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE constraint_type = 'FOREIGN KEY'
                ORDER BY tc.table_name, kcu.column_name;
            """
            
            relationships = await self.db_manager.execute_query(fk_query)
            
            if not relationships:
                result = "-- No se encontraron relaciones de clave foránea"
            else:
                parts = ["RELACIONES ENTRE TABLAS"]
                parts.append("=" * 25)
                
                for rel in relationships:
                    rel_desc = (
                        f"{rel['table_name']}.{rel['column_name']} -> "
                        f"{rel['foreign_table_name']}.{rel['foreign_column_name']}"
                    )
                    parts.append(f"  - {rel_desc}")
                
                result = "\n".join(parts)
            
            # Cachear resultado
            self._cache[cache_key] = result
            self._last_update[cache_key] = datetime.now()
            
            logger.info(f"Relationships generated: {len(relationships)} found")
            return result
            
        except Exception as e:
            logger.error(f"Error generating relationships: {str(e)}")
            return "-- Error obteniendo relaciones"
    
    async def get_few_shot_examples(self) -> str:
        """
        Obtiene ejemplos few-shot para mejorar las consultas SQL
        
        Returns:
            String con ejemplos formateados
        """
        cache_key = "few_shot_examples"
        
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            # Ejemplos predefinidos que se pueden personalizar según el dominio
            examples = [
                {
                    "query": "ventas totales del último mes",
                    "sql": "SELECT SUM(monto) as total_ventas FROM ventas WHERE fecha >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month') AND fecha < date_trunc('month', CURRENT_DATE)",
                    "explanation": "Suma todas las ventas del mes anterior usando date_trunc para obtener rangos exactos"
                },
                {
                    "query": "top 10 productos más vendidos",
                    "sql": "SELECT p.nombre, SUM(v.cantidad) as total_vendido FROM productos p JOIN ventas v ON p.id = v.producto_id GROUP BY p.id, p.nombre ORDER BY total_vendido DESC LIMIT 10",
                    "explanation": "Join entre productos y ventas, agrupado por producto y ordenado por cantidad descendente"
                },
                {
                    "query": "comparar ventas por región este año vs año pasado",
                    "sql": "SELECT r.nombre as region, SUM(CASE WHEN EXTRACT(year FROM v.fecha) = EXTRACT(year FROM CURRENT_DATE) THEN v.monto ELSE 0 END) as ventas_este_ano, SUM(CASE WHEN EXTRACT(year FROM v.fecha) = EXTRACT(year FROM CURRENT_DATE) - 1 THEN v.monto ELSE 0 END) as ventas_ano_pasado FROM regiones r JOIN ventas v ON r.id = v.region_id GROUP BY r.id, r.nombre",
                    "explanation": "Uso de CASE WHEN para comparar años en la misma query, agrupado por región"
                }
            ]
            
            parts = ["EJEMPLOS DE CONSULTAS"]
            parts.append("=" * 20)
            
            for i, example in enumerate(examples, 1):
                parts.append(f"\nEjemplo {i}:")
                parts.append(f"Consulta: \"{example['query']}\"")
                parts.append(f"SQL: {example['sql']}")
                parts.append(f"Explicación: {example['explanation']}")
            
            result = "\n".join(parts)
            
            # Cachear resultado
            self._cache[cache_key] = result
            self._last_update[cache_key] = datetime.now()
            
            logger.info("Few-shot examples generated")
            return result
            
        except Exception as e:
            logger.error(f"Error generating few-shot examples: {str(e)}")
            return "-- Error generando ejemplos"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        Verifica si el cache es válido para una clave
        
        Args:
            cache_key: Clave del cache
            
        Returns:
            True si el cache es válido
        """
        if cache_key not in self._cache:
            return False
        
        if cache_key not in self._last_update:
            return False
        
        time_since_update = datetime.now() - self._last_update[cache_key]
        return time_since_update < self._cache_ttl
    
    def clear_cache(self):
        """Limpia todo el cache"""
        self._cache.clear()
        self._last_update.clear()
        logger.info("Metadata cache cleared")
    
    async def refresh_cache(self):
        """Refresca todo el cache"""
        self.clear_cache()
        await self.get_full_schema()
        await self.get_data_dictionary()
        await self.get_relationships()
        await self.get_few_shot_examples()
        logger.info("Metadata cache refreshed")