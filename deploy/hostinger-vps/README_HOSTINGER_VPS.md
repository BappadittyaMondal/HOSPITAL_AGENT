# HOSTINGER KVM LINUX VPS DEPLOYMENT GUIDE (PRODUCTION-READY)

This guide provides the complete, turnkey procedure for deploying **HOSPITAL_AGENT** to a **Hostinger KVM Linux VPS** (Ubuntu 22.04 / 24.04 LTS) when upgrading from the free local environment.

---

## 1. Prerequisites on Hostinger
- **VPS Plan:** Hostinger KVM 1, KVM 2, or higher running **Ubuntu 22.04 LTS** or **Ubuntu 24.04 LTS**.
- **Domain / DNS:** A domain or subdomain (e.g. `api.hospital-agent.org` or `hospital.yourdomain.com`) pointing via an `A Record` to your Hostinger VPS IPv4 address.
- **SSH Access:** Root or sudo-enabled user access via SSH:
  ```bash
  ssh root@<YOUR_VPS_IP>
  ```

---

## 2. One-Command Automated Setup

Once connected to your Hostinger VPS via SSH, run the automated setup script:

```bash
# 1. Clone the repository from Git
git clone https://github.com/<YOUR_GITHUB_USER>/HOSPITAL_AGENT.git /opt/hospital_agent

# 2. Enter deployment directory
cd /opt/hospital_agent/deploy/hostinger-vps

# 3. Make the setup script executable and run
chmod +x setup_vps.sh
sudo ./setup_vps.sh
```

The script automatically:
1. Updates package repositories (`apt update && apt upgrade`).
2. Installs Python 3.11/3.12, `python3-venv`, `python3-pip`, `nginx`, `git`, and `curl`.
3. Creates a dedicated application user `hospital`.
4. Creates a Python virtual environment at `/opt/hospital_agent/venv`.
5. Installs all project dependencies from `requirements.txt`.
6. Configures and enables the `hospital_agent.service` systemd daemon.
7. Installs and configures Nginx reverse proxy routing traffic from port 80/443 to Uvicorn on port 8000.
8. Obtains a free Let's Encrypt SSL/TLS 1.3 certificate (optional via Certbot).

---

## 3. Manual Step-by-Step Architecture (Alternative)

If you prefer manual configuration:

### Step 3.1: Install System Packages
```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nginx git certbot python3-certbot-nginx
```

### Step 3.2: Python Virtual Environment
```bash
cd /opt/hospital_agent
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3.3: Environment Variables
Copy `.env.example` to `.env` and configure production secrets:
```bash
cp .env.example .env
nano .env
# Set HOSPITAL_ENV=production
# Set JWT_SECRET_KEY=<RANDOM_64_CHAR_HEX>
```

### Step 3.4: Configure Systemd Service
```bash
sudo cp /opt/hospital_agent/deploy/hostinger-vps/hospital_agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hospital_agent
sudo systemctl start hospital_agent
sudo systemctl status hospital_agent
```

### Step 3.5: Configure Nginx Reverse Proxy
```bash
sudo cp /opt/hospital_agent/deploy/hostinger-vps/nginx_hospital_agent.conf /etc/nginx/sites-available/hospital_agent
sudo ln -s /etc/nginx/sites-available/hospital_agent /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### Step 3.6: Activate Free SSL/TLS (Let's Encrypt)
```bash
sudo certbot --nginx -d your-domain.com
```

---

## 4. Useful Service Management Commands on Hostinger VPS

| Action | Command |
| :--- | :--- |
| **Check Service Status** | `sudo systemctl status hospital_agent` |
| **Restart Application** | `sudo systemctl restart hospital_agent` |
| **View Live Clinical Logs** | `sudo journalctl -u hospital_agent -f` |
| **Restart Nginx** | `sudo systemctl restart nginx` |
| **Run Regression Suite on VPS** | `source /opt/hospital_agent/venv/bin/activate && python /opt/hospital_agent/tests/run_all_phase_runners.py` |
| **Run DRE Clinical Safety Gate** | `source /opt/hospital_agent/venv/bin/activate && python /opt/hospital_agent/scripts/run_clinical_safety_regression.py` |

---

## 5. Why Hostinger KVM Linux VPS vs Shared Hosting?
- **No Process Killing:** Shared cPanel hosting terminates long-running Python processes after 30–60 seconds. KVM Linux VPS runs continuous daemon processes with 99.9% uptime.
- **WebSocket & Real-Time Telemetry:** Supports continuous bi-directional telemetry sockets for rural ICU and emergency triage kiosks.
- **Dedicated Memory & CPU:** Unthrottled sub-2ms deterministic rule execution (DRE).
