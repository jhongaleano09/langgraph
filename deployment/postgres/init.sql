-- Script de inicialización de la base de datos
-- Este script se ejecuta automáticamente cuando se crea el contenedor PostgreSQL

-- Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Crear tablas de ejemplo para pruebas
-- Tabla de ventas por región
CREATE TABLE IF NOT EXISTS sales_by_region (
    id SERIAL PRIMARY KEY,
    region VARCHAR(100) NOT NULL,
    quarter VARCHAR(10) NOT NULL,
    sales_amount DECIMAL(15, 2) NOT NULL,
    product_category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar datos de ejemplo
INSERT INTO sales_by_region (region, quarter, sales_amount, product_category) VALUES
('Norte', 'Q1-2024', 150000.00, 'Tecnología'),
('Norte', 'Q2-2024', 180000.00, 'Tecnología'),
('Norte', 'Q3-2024', 220000.00, 'Tecnología'),
('Norte', 'Q4-2024', 250000.00, 'Tecnología'),
('Sur', 'Q1-2024', 120000.00, 'Hogar'),
('Sur', 'Q2-2024', 140000.00, 'Hogar'),
('Sur', 'Q3-2024', 160000.00, 'Hogar'),
('Sur', 'Q4-2024', 180000.00, 'Hogar'),
('Este', 'Q1-2024', 200000.00, 'Automóviles'),
('Este', 'Q2-2024', 210000.00, 'Automóviles'),
('Este', 'Q3-2024', 230000.00, 'Automóviles'),
('Este', 'Q4-2024', 240000.00, 'Automóviles'),
('Oeste', 'Q1-2024', 100000.00, 'Ropa'),
('Oeste', 'Q2-2024', 110000.00, 'Ropa'),
('Oeste', 'Q3-2024', 125000.00, 'Ropa'),
('Oeste', 'Q4-2024', 135000.00, 'Ropa');

-- Tabla de empleados
CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    position VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    salary DECIMAL(10, 2) NOT NULL,
    hire_date DATE NOT NULL,
    region VARCHAR(100) NOT NULL
);

-- Insertar empleados de ejemplo
INSERT INTO employees (name, position, department, salary, hire_date, region) VALUES
('Ana García', 'Gerente de Ventas', 'Ventas', 85000.00, '2022-01-15', 'Norte'),
('Carlos López', 'Analista', 'Tecnología', 65000.00, '2023-03-10', 'Norte'),
('María Rodríguez', 'Coordinadora', 'Marketing', 55000.00, '2023-06-20', 'Sur'),
('Juan Pérez', 'Desarrollador', 'Tecnología', 70000.00, '2022-08-05', 'Este'),
('Laura Martín', 'Diseñadora', 'Marketing', 60000.00, '2023-01-12', 'Oeste');

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO chatbot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO chatbot_user;