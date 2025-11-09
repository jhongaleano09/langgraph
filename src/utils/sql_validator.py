"""
SQL Validator
Valida consultas SQL antes de ejecución para seguridad
"""
import logging
import re
from typing import Dict, Any, List
import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DML

from ..utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SQLValidator:
    """
    Validador de consultas SQL para prevenir inyecciones y operaciones peligrosas
    """
    
    def __init__(self):
        # Palabras clave permitidas (solo SELECT y operaciones de lectura)
        self.allowed_keywords = {
            'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'OUTER',
            'ON', 'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'ILIKE',
            'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET', 'DISTINCT',
            'AS', 'ASC', 'DESC', 'NULL', 'IS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
            'UNION', 'INTERSECT', 'EXCEPT', 'WITH', 'RECURSIVE', 'CAST', 'EXTRACT',
            'DATE_TRUNC', 'COALESCE', 'NULLIF', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN',
            'STRING_AGG', 'ARRAY_AGG', 'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'OVER',
            'PARTITION', 'WINDOW', 'CURRENT_DATE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP',
            'INTERVAL', 'NOW', 'GREATEST', 'LEAST', 'SUBSTRING', 'LENGTH', 'TRIM',
            'UPPER', 'LOWER', 'REPLACE', 'CONCAT', 'POSITION', 'SPLIT_PART'
        }
        
        # Palabras clave prohibidas (operaciones de escritura y peligrosas)
        self.forbidden_keywords = {
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE',
            'GRANT', 'REVOKE', 'EXECUTE', 'CALL', 'DECLARE', 'SET', 'RESET',
            'COPY', 'BULK', 'LOAD', 'UNLOAD', 'BACKUP', 'RESTORE', 'MERGE',
            'UPSERT', 'EXPLAIN', 'ANALYZE', 'VACUUM', 'CLUSTER', 'REINDEX'
        }
        
        # Patrones peligrosos
        self.dangerous_patterns = [
            r';',  # Múltiples sentencias
            r'--',  # Comentarios SQL
            r'/\*.*?\*/',  # Comentarios de bloque
            r'xp_cmdshell',  # Comandos del sistema
            r'sp_',  # Procedimientos almacenados
            r'exec\s*\(',  # Ejecución de comandos
            r'eval\s*\(',  # Evaluación dinámica
            r'\$\$',  # Bloques de código PostgreSQL
        ]
        
        # Límites de seguridad
        self.max_query_length = 5000
        self.max_result_limit = 10000
        self.default_limit = 1000
    
    async def validate_sql(self, sql_query: str) -> Dict[str, Any]:
        """
        Valida una consulta SQL completa
        
        Args:
            sql_query: Consulta SQL a validar
            
        Returns:
            Dict con resultado de validación
        """
        try:
            logger.info("Validating SQL query")
            
            # Lista de errores encontrados
            errors = []
            warnings = []
            
            # 1. Validaciones básicas
            basic_validation = self._validate_basic_security(sql_query)
            if not basic_validation['valid']:
                errors.extend(basic_validation['errors'])
            
            # 2. Parsear SQL
            try:
                parsed = sqlparse.parse(sql_query)
                if not parsed:
                    errors.append("No se pudo parsear la consulta SQL")
                else:
                    # 3. Validar estructura
                    structure_validation = self._validate_structure(parsed[0])
                    if not structure_validation['valid']:
                        errors.extend(structure_validation['errors'])
                    warnings.extend(structure_validation.get('warnings', []))
                    
                    # 4. Validar keywords
                    keyword_validation = self._validate_keywords(parsed[0])
                    if not keyword_validation['valid']:
                        errors.extend(keyword_validation['errors'])
                    
            except Exception as e:
                errors.append(f"Error parseando SQL: {str(e)}")
            
            # 5. Validar límites
            limit_validation = self._validate_limits(sql_query)
            if not limit_validation['valid']:
                errors.extend(limit_validation['errors'])
            warnings.extend(limit_validation.get('warnings', []))
            
            # 6. Agregar LIMIT si no existe
            safe_query = self._ensure_limit(sql_query)
            
            is_valid = len(errors) == 0
            
            result = {
                'valid': is_valid,
                'safe_query': safe_query if is_valid else None,
                'original_query': sql_query,
                'errors': errors,
                'warnings': warnings,
                'security_score': self._calculate_security_score(sql_query, errors, warnings)
            }
            
            logger.info(f"SQL validation completed - Valid: {is_valid}")
            return result
            
        except Exception as e:
            logger.error(f"Error in SQL validation: {str(e)}")
            return {
                'valid': False,
                'safe_query': None,
                'original_query': sql_query,
                'errors': [f"Error en validación: {str(e)}"],
                'warnings': [],
                'security_score': 0.0
            }
    
    def _validate_basic_security(self, sql_query: str) -> Dict[str, Any]:
        """Validaciones básicas de seguridad"""
        errors = []
        
        # Longitud máxima
        if len(sql_query) > self.max_query_length:
            errors.append(f"Consulta muy larga (máximo {self.max_query_length} caracteres)")
        
        # Consulta vacía
        if not sql_query.strip():
            errors.append("Consulta vacía")
        
        # Patrones peligrosos
        for pattern in self.dangerous_patterns:
            if re.search(pattern, sql_query, re.IGNORECASE):
                errors.append(f"Patrón peligroso detectado: {pattern}")
        
        # Múltiples sentencias (buscar ; que no esté al final)
        clean_query = sql_query.strip()
        semicolons = [m.start() for m in re.finditer(';', clean_query)]
        if semicolons and semicolons[-1] != len(clean_query) - 1:
            errors.append("Múltiples sentencias SQL no permitidas")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _validate_structure(self, parsed_statement: Statement) -> Dict[str, Any]:
        """Valida la estructura de la consulta parseada"""
        errors = []
        warnings = []
        
        # Verificar que sea una consulta SELECT
        first_token = None
        for token in parsed_statement.tokens:
            if token.ttype is Keyword and token.value.upper() == 'SELECT':
                first_token = token
                break
            elif token.ttype is DML:
                first_token = token
                break
        
        if not first_token or first_token.value.upper() != 'SELECT':
            errors.append("Solo se permiten consultas SELECT")
        
        # Verificar anidamiento excesivo
        query_str = str(parsed_statement)
        subquery_count = query_str.count('(') + query_str.count('SELECT')
        if subquery_count > 10:
            warnings.append("Consulta muy compleja con múltiples subconsultas")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_keywords(self, parsed_statement: Statement) -> Dict[str, Any]:
        """Valida que solo se usen keywords permitidas"""
        errors = []
        
        def check_token(token):
            if token.ttype is Keyword:
                keyword = token.value.upper()
                if keyword in self.forbidden_keywords:
                    errors.append(f"Palabra clave prohibida: {keyword}")
                elif keyword not in self.allowed_keywords:
                    # Verificar si es una función conocida
                    if not self._is_known_function(keyword):
                        errors.append(f"Palabra clave no reconocida: {keyword}")
            
            # Recursivamente verificar tokens anidados
            if hasattr(token, 'tokens'):
                for subtoken in token.tokens:
                    check_token(subtoken)
        
        for token in parsed_statement.tokens:
            check_token(token)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _is_known_function(self, keyword: str) -> bool:
        """Verifica si una palabra clave es una función conocida"""
        known_functions = {
            'CURRENT_USER', 'SESSION_USER', 'USER', 'VERSION', 'PG_BACKEND_PID',
            'TO_CHAR', 'TO_DATE', 'TO_NUMBER', 'TO_TIMESTAMP', 'AGE', 'CLOCK_TIMESTAMP',
            'TIMEOFDAY', 'TRANSACTION_TIMESTAMP', 'STATEMENT_TIMESTAMP',
            'MD5', 'SHA1', 'SHA224', 'SHA256', 'SHA384', 'SHA512',
            'ENCODE', 'DECODE', 'FORMAT', 'LPAD', 'RPAD', 'REPEAT',
            'REVERSE', 'TRANSLATE', 'ASCII', 'CHR', 'INITCAP',
            'ABS', 'CEIL', 'CEILING', 'FLOOR', 'ROUND', 'TRUNC', 'SIGN',
            'EXP', 'LN', 'LOG', 'POWER', 'SQRT', 'RANDOM',
            'SIN', 'COS', 'TAN', 'ASIN', 'ACOS', 'ATAN', 'ATAN2',
            'DEGREES', 'RADIANS', 'PI'
        }
        return keyword in known_functions
    
    def _validate_limits(self, sql_query: str) -> Dict[str, Any]:
        """Valida límites de resultados"""
        errors = []
        warnings = []
        
        # Buscar LIMIT en la consulta
        limit_match = re.search(r'LIMIT\s+(\d+)', sql_query, re.IGNORECASE)
        if limit_match:
            limit_value = int(limit_match.group(1))
            if limit_value > self.max_result_limit:
                errors.append(f"LIMIT muy alto (máximo {self.max_result_limit})")
        else:
            warnings.append(f"Se agregará LIMIT {self.default_limit} por seguridad")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _ensure_limit(self, sql_query: str) -> str:
        """Asegura que la consulta tenga un LIMIT apropiado"""
        # Si ya tiene LIMIT, no modificar
        if re.search(r'LIMIT\s+\d+', sql_query, re.IGNORECASE):
            return sql_query
        
        # Agregar LIMIT al final
        clean_query = sql_query.strip()
        if clean_query.endswith(';'):
            clean_query = clean_query[:-1]
        
        return f"{clean_query} LIMIT {self.default_limit};"
    
    def _calculate_security_score(
        self, 
        sql_query: str, 
        errors: List[str], 
        warnings: List[str]
    ) -> float:
        """Calcula un score de seguridad (0-10)"""
        base_score = 10.0
        
        # Penalizar errores gravemente
        base_score -= len(errors) * 3.0
        
        # Penalizar warnings levemente
        base_score -= len(warnings) * 0.5
        
        # Penalizar consultas muy largas
        if len(sql_query) > 1000:
            base_score -= 1.0
        
        # Penalizar muchos JOINs (complejidad)
        join_count = len(re.findall(r'JOIN', sql_query, re.IGNORECASE))
        if join_count > 5:
            base_score -= join_count * 0.2
        
        return max(0.0, min(10.0, base_score))