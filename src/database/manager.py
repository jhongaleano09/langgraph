"""
Database Manager
Maneja las conexiones y operaciones de base de datos
"""
import logging
from typing import List, Dict, Any, Optional
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager

from ..utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DatabaseManager:
    """
    Gestor de base de datos con soporte para operaciones síncronas y asíncronas
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.async_engine = None
        self.session_factory = None
        self.async_session_factory = None
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Inicializa los engines de SQLAlchemy"""
        try:
            # Engine síncrono
            self.engine = create_engine(
                self.settings.database_url,
                echo=self.settings.debug,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            
            # Engine asíncrono
            async_url = self.settings.database_url.replace('postgresql://', 'postgresql+asyncpg://')
            self.async_engine = create_async_engine(
                async_url,
                echo=self.settings.debug,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            
            # Session factories
            self.session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
            
            self.async_session_factory = sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False
            )
            
            logger.info("Database engines initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database engines: {str(e)}")
            raise
    
    @asynccontextmanager
    async def get_async_session(self):
        """Context manager para sesiones asíncronas"""
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {str(e)}")
                raise
            finally:
                await session.close()
    
    async def execute_query(
        self, 
        sql_query: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta una consulta SQL y retorna los resultados
        
        Args:
            sql_query: Consulta SQL a ejecutar
            params: Parámetros para la consulta
            
        Returns:
            Lista de diccionarios con los resultados
        """
        try:
            logger.info(f"Executing query: {sql_query[:100]}...")
            
            async with self.get_async_session() as session:
                # Ejecutar la consulta
                result = await session.execute(
                    text(sql_query), 
                    params or {}
                )
                
                # Convertir a lista de diccionarios
                columns = result.keys()
                rows = result.fetchall()
                
                data = [
                    {col: value for col, value in zip(columns, row)} 
                    for row in rows
                ]
                
                logger.info(f"Query executed successfully, {len(data)} rows returned")
                return data
                
        except SQLAlchemyError as e:
            logger.error(f"Database error executing query: {str(e)}")
            raise DatabaseError(f"Error ejecutando consulta: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise DatabaseError(f"Error inesperado: {str(e)}")
    
    async def test_connection(self) -> bool:
        """
        Prueba la conexión a la base de datos
        
        Returns:
            True si la conexión es exitosa
        """
        try:
            async with self.get_async_session() as session:
                await session.execute(text("SELECT 1"))
                logger.info("Database connection test successful")
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False
    
    async def get_table_names(self) -> List[str]:
        """
        Obtiene los nombres de todas las tablas en la base de datos
        
        Returns:
            Lista de nombres de tablas
        """
        try:
            query = """
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """
            
            result = await self.execute_query(query)
            return [row['tablename'] for row in result]
            
        except Exception as e:
            logger.error(f"Error getting table names: {str(e)}")
            return []
    
    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Obtiene información detallada de una tabla
        
        Args:
            table_name: Nombre de la tabla
            
        Returns:
            Diccionario con información de la tabla
        """
        try:
            # Obtener columnas
            columns_query = """
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale
                FROM information_schema.columns
                WHERE table_name = :table_name
                ORDER BY ordinal_position;
            """
            
            columns = await self.execute_query(
                columns_query, 
                {"table_name": table_name}
            )
            
            # Obtener claves primarias
            pk_query = """
                SELECT column_name
                FROM information_schema.key_column_usage k
                JOIN information_schema.table_constraints t
                    ON k.constraint_name = t.constraint_name
                WHERE t.table_name = :table_name
                    AND t.constraint_type = 'PRIMARY KEY';
            """
            
            primary_keys = await self.execute_query(
                pk_query, 
                {"table_name": table_name}
            )
            
            # Obtener claves foráneas
            fk_query = """
                SELECT 
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.key_column_usage AS kcu
                JOIN information_schema.table_constraints AS tc 
                    ON kcu.constraint_name = tc.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu 
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = :table_name;
            """
            
            foreign_keys = await self.execute_query(
                fk_query, 
                {"table_name": table_name}
            )
            
            # Obtener estadísticas de la tabla
            stats_query = """
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    correlation
                FROM pg_stats
                WHERE tablename = :table_name;
            """
            
            stats = await self.execute_query(
                stats_query, 
                {"table_name": table_name}
            )
            
            return {
                "table_name": table_name,
                "columns": columns,
                "primary_keys": [pk["column_name"] for pk in primary_keys],
                "foreign_keys": foreign_keys,
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Error getting table info for {table_name}: {str(e)}")
            return {
                "table_name": table_name,
                "columns": [],
                "primary_keys": [],
                "foreign_keys": [],
                "statistics": []
            }
    
    async def get_sample_data(
        self, 
        table_name: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Obtiene datos de muestra de una tabla
        
        Args:
            table_name: Nombre de la tabla
            limit: Número máximo de filas
            
        Returns:
            Lista de diccionarios con datos de muestra
        """
        try:
            query = f"SELECT * FROM {table_name} LIMIT :limit"
            return await self.execute_query(query, {"limit": limit})
        except Exception as e:
            logger.error(f"Error getting sample data from {table_name}: {str(e)}")
            return []
    
    def close_connections(self):
        """Cierra todas las conexiones"""
        try:
            if self.engine:
                self.engine.dispose()
            if self.async_engine:
                asyncio.create_task(self.async_engine.dispose())
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {str(e)}")


class DatabaseError(Exception):
    """Excepción personalizada para errores de base de datos"""
    pass


# Instancia global del manager
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """
    Obtiene la instancia global del DatabaseManager
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager