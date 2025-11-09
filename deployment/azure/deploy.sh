#!/bin/bash

# Azure VM Deployment Script for Text-to-Report Chatbot
# Usage: ./deploy.sh

set -e

echo "🚀 Iniciando deployment en Azure VM..."

# Variables de configuración
APP_NAME="text-to-report-chatbot"
DOMAIN_NAME=${DOMAIN_NAME:-"localhost"}
SSL_EMAIL=${SSL_EMAIL:-"admin@example.com"}
ENVIRONMENT=${ENVIRONMENT:-"production"}

# Colores para logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar que estamos ejecutando como usuario con permisos sudo
if [[ $EUID -eq 0 ]]; then
   log_error "No ejecutes este script como root. Usa un usuario con permisos sudo."
   exit 1
fi

# 1. Actualizar sistema
log_info "Actualizando sistema..."
sudo apt update && sudo apt upgrade -y

# 2. Instalar dependencias del sistema
log_info "Instalando dependencias del sistema..."
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    nginx \
    git \
    htop \
    unzip

# 3. Instalar Docker
log_info "Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io
    sudo usermod -aG docker $USER
    log_info "Docker instalado. Es necesario reiniciar la sesión."
else
    log_info "Docker ya está instalado."
fi

# 4. Instalar Docker Compose
log_info "Instalando Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
else
    log_info "Docker Compose ya está instalado."
fi

# 5. Configurar firewall
log_info "Configurando firewall..."
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw allow 80
sudo ufw allow 443
sudo ufw --force enable

# 6. Configurar directorio de la aplicación
log_info "Configurando directorio de aplicación..."
sudo mkdir -p /opt/${APP_NAME}
sudo chown -R $USER:$USER /opt/${APP_NAME}

# 7. Si el repositorio no existe, clonarlo
if [ ! -d "/opt/${APP_NAME}/.git" ]; then
    log_info "Clonando repositorio..."
    # Nota: Reemplaza con tu URL de repositorio real
    # git clone https://github.com/tu-usuario/text-to-report-chatbot.git /opt/${APP_NAME}
    log_warn "Por favor, clona el repositorio manualmente en /opt/${APP_NAME}"
else
    log_info "Repositorio ya existe, actualizando..."
    cd /opt/${APP_NAME}
    git pull origin main
fi

# 8. Configurar variables de entorno
log_info "Configurando variables de entorno..."
cd /opt/${APP_NAME}

if [ ! -f ".env" ]; then
    cp .env.example .env
    log_warn "Por favor, edita el archivo .env con tus configuraciones reales:"
    log_warn "nano /opt/${APP_NAME}/.env"
    log_warn "Presiona Enter cuando hayas terminado de configurar..."
    read -r
fi

# 9. Crear directorios necesarios
log_info "Creando directorios necesarios..."
mkdir -p generated_reports logs temp uploads static

# 10. Configurar Nginx
log_info "Configurando Nginx..."
sudo cp deployment/nginx/chatbot.conf /etc/nginx/sites-available/${APP_NAME}
sudo ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Reemplazar variables en configuración de Nginx
sudo sed -i "s/your-domain.com/${DOMAIN_NAME}/g" /etc/nginx/sites-available/${APP_NAME}
sudo sed -i "s|/path/to/app|/opt/${APP_NAME}|g" /etc/nginx/sites-available/${APP_NAME}

# Verificar configuración de Nginx
sudo nginx -t

# 11. Configurar SSL con Certbot (si no es localhost)
if [ "$DOMAIN_NAME" != "localhost" ] && [ "$DOMAIN_NAME" != "127.0.0.1" ]; then
    log_info "Configurando SSL con Certbot..."
    sudo apt install -y snapd
    sudo snap install core; sudo snap refresh core
    sudo snap install --classic certbot
    sudo ln -sf /snap/bin/certbot /usr/bin/certbot
    
    log_info "Ejecutando Certbot..."
    sudo certbot --nginx -d ${DOMAIN_NAME} --email ${SSL_EMAIL} --agree-tos --non-interactive
fi

# 12. Construir y ejecutar contenedores
log_info "Construyendo y ejecutando contenedores..."
docker-compose down --remove-orphans
docker-compose build
docker-compose up -d

# 13. Esperar a que los servicios estén listos
log_info "Esperando a que los servicios estén listos..."
sleep 30

# 14. Ejecutar migraciones de base de datos
log_info "Ejecutando migraciones de base de datos..."
docker-compose exec -T app poetry run alembic upgrade head

# 15. Configurar servicios del sistema
log_info "Configurando servicios del sistema..."

# Crear archivo de servicio systemd para auto-start
sudo tee /etc/systemd/system/${APP_NAME}.service > /dev/null <<EOF
[Unit]
Description=Text-to-Report Chatbot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/${APP_NAME}
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable ${APP_NAME}.service

# 16. Reiniciar Nginx
log_info "Reiniciando Nginx..."
sudo systemctl restart nginx

# 17. Verificar estado de servicios
log_info "Verificando estado de servicios..."
docker-compose ps

# 18. Mostrar información final
log_info "✅ Deployment completado!"
echo ""
echo "📋 Información del deployment:"
echo "  - Aplicación: http://${DOMAIN_NAME}"
echo "  - API: http://${DOMAIN_NAME}/api/v1"
echo "  - LangGraph API: http://${DOMAIN_NAME}:8123"
echo "  - Grafana: http://${DOMAIN_NAME}:3000 (admin/admin123)"
echo "  - Prometheus: http://${DOMAIN_NAME}:9090"
echo ""
echo "📝 Próximos pasos:"
echo "  1. Verificar que el archivo .env está configurado correctamente"
echo "  2. Cargar datos de ejemplo en la base de datos"
echo "  3. Probar la funcionalidad con queries de ejemplo"
echo ""
echo "🔧 Comandos útiles:"
echo "  - Ver logs: cd /opt/${APP_NAME} && docker-compose logs -f"
echo "  - Reiniciar: cd /opt/${APP_NAME} && docker-compose restart"
echo "  - Actualizar: cd /opt/${APP_NAME} && git pull && docker-compose up -d --build"

log_info "🎉 Deployment finalizado exitosamente!"