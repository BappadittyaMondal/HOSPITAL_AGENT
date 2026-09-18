#!/usr/bin/env bash
# ====================================================================================================
# PROJECT "HOSPITAL" — HOSTINGER KVM LINUX VPS AUTOMATED PROVISIONING SCRIPT
# ====================================================================================================
# Target OS: Ubuntu 22.04 LTS / Ubuntu 24.04 LTS
# Target Environment: Hostinger KVM Linux VPS
# Usage: sudo ./setup_vps.sh
# ====================================================================================================

set -e

echo "===================================================================================================="
echo "          PROVISIONING HOSPITAL_AGENT ON HOSTINGER KVM LINUX VPS"
echo "===================================================================================================="

# Check root permissions
if [ "$EUID" -ne 0 ]; then
  echo "[ERROR] Please run as root or with sudo: sudo ./setup_vps.sh"
  exit 1
fi

APP_DIR="/opt/hospital_agent"
CURRENT_DIR="$(pwd)"

echo "[1/6] Updating system packages..."
apt-get update -y && apt-get upgrade -y

echo "[2/6] Installing Python, venv, Nginx, and essential build tools..."
apt-get install -y python3 python3-pip python3-venv nginx git curl ufw

# Configure UFW Firewall
echo "[3/6] Configuring UFW Firewall..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# Virtual Environment Setup
echo "[4/6] Setting up Python virtual environment..."
mkdir -p "$APP_DIR"
if [ ! -d "$APP_DIR/venv" ]; then
    python3 -m venv "$APP_DIR/venv"
fi

"$APP_DIR/venv/bin/pip" install --upgrade pip setuptools wheel
if [ -f "$CURRENT_DIR/../../requirements.txt" ]; then
    "$APP_DIR/venv/bin/pip" install -r "$CURRENT_DIR/../../requirements.txt"
elif [ -f "$APP_DIR/requirements.txt" ]; then
    "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
fi

# Configure Systemd Service
echo "[5/6] Configuring systemd service (hospital_agent.service)..."
if [ -f "$CURRENT_DIR/hospital_agent.service" ]; then
    cp "$CURRENT_DIR/hospital_agent.service" /etc/systemd/system/
fi
systemctl daemon-reload
systemctl enable hospital_agent.service
systemctl restart hospital_agent.service

# Configure Nginx
echo "[6/6] Configuring Nginx reverse proxy..."
if [ -f "$CURRENT_DIR/nginx_hospital_agent.conf" ]; then
    cp "$CURRENT_DIR/nginx_hospital_agent.conf" /etc/nginx/sites-available/hospital_agent
    ln -sf /etc/nginx/sites-available/hospital_agent /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t
    systemctl restart nginx
fi

echo "===================================================================================================="
echo " [SUCCESS] HOSPITAL_AGENT is live on your Hostinger KVM Linux VPS!"
echo " Service Status: $(systemctl is-active hospital_agent)"
echo " Nginx Status:   $(systemctl is-active nginx)"
echo ""
echo " Next Step (Optional SSL):"
echo " sudo apt install -y certbot python3-certbot-nginx"
echo " sudo certbot --nginx -d your-domain.com"
echo "===================================================================================================="
