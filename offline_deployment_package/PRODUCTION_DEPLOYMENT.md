# eTabib Production Deployment Guide (Offline & Secure)

This document serves as the master guide for deploying the **eTabib** solution on a production server (Ubuntu Server 24.04), specifically tailored for an **offline** environment with **SafeLine WAF** protection.

**Last Updated:** December 2025

---

## 1. Prerequisites

*   **Server**: Ubuntu Server 24.04 LTS (Physical Machine)
*   **Storage**:
    *   `/dev/sda`: OS Installation (Boot)
    *   `/mnt/live_data`: Data Partition (SSD Partition 2) - **ALL persistent data resides here.**
*   **Network**:
    *   Server IP (LAN): `192.168.1.65`
    *   Public IP: `105.96.26.230` (Static or Dynamic)
    *   Box Internet: ZTE (Port Forwarding enabled)
*   **Security Tools**:
    *   **SafeLine WAF** (Web Application Firewall)
    *   **UFW** (Ubuntu Firewall)

---

## 2. Initial Server Setup (SSH & Security)

### Step 1: Secure SSH Access
1.  **Port**: Change SSH port to `7722`.
2.  **Auth**: Disable Password Authentication, use SSH Keys only.
3.  **Root**: Disable Root Login.

**Connection Command:**
```bash
ssh -p 7722 serv_etb_2026@192.168.1.65
```

### Step 2: Firewall (UFW) Configuration
Open only the strictly necessary ports. SafeLine will handle Web traffic.
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 7722/tcp  # SSH Management
sudo ufw allow 80/tcp    # SafeLine HTTP
sudo ufw allow 443/tcp   # SafeLine HTTPS
sudo ufw allow 9443/tcp  # SafeLine Management UI
sudo ufw allow 10000/udp # Jitsi Video Bridge
sudo ufw allow 4443/tcp  # Jitsi TCP Fallback
sudo ufw enable
```

---

## 3. Docker Installation (Offline Friendly)
*Assumes Docker .deb packages are transferred via USB if no internet.*

**Verification:**
```bash
docker --version
docker compose version
```

---

## 4. Deployment Package Setup

All deployment files are located in `/mnt/live_data/etabib_project/offline_deployment_package`.

### Automated Setup (Recommended)
We have created a script to automate the extraction of data and placement of configuration files.

1.  **Navigate to the package folder:**
    ```bash
    cd /mnt/live_data/etabib_project/offline_deployment_package
    ```
2.  **Run the automation script:**
    ```bash
    chmod +x deploy_step_3.sh
    ./deploy_step_3.sh
    ```
    *This script extracts `media_backup.tar.gz`, `static_backup.tar.gz`, moves configurations, and sets initial permissions.*

### Manual Fallback (If script fails)
```bash
# Extract data
tar -xzf media_backup.tar.gz -C ../
tar -xzf static_backup.tar.gz -C ../
# (Note: Tuned mysql config is intentionally ignored/commented out in compose)
```

---

## 5. Service Configuration

### docker-compose.prod.yml
The production configuration includes:
*   **Persistent Volumes**: Mapped to `/mnt/live_data/etabib_project/...`
*   **Settings Patch**: Mounts a patched `settings.py` to allow dynamic `ALLOWED_HOSTS`.
*   **Resource Limits**: RAM limits for Web (4G), DB (6G), Ollama (8G).

**Critical Check:** Ensure `settings.py` is mounted:
```yaml
  web:
    volumes:
      - /mnt/live_data/etabib_project/offline_deployment_package/settings.py:/app/etabibWebsite/settings.py
      # ... other volumes
```

### .env.prod Configuration
This file stores your secrets. It MUST be updated with your specific domain names and IPs to avoid "Bad Request (400)" errors.

**Required `ALLOWED_HOSTS`:**
```ini
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.65,105.96.26.230,etabib_web,store.etabib.dz,api.etabib.dz,www.api.etabib.dz,visio.etabib.dz,mystore.etabib.dz
```
*Note: Include all subdomains and your Public IP.*

---

## 6. Launch & Data Restoration

### Step 1: Start Services
```bash
cd /mnt/live_data/etabib_project/offline_deployment_package
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.jitsi.yml up -d
```

### Step 2: Restore Database
Use the reliable 2-step method:
```bash
# 1. Copy dump to container
docker cp etabibstore_backup.sql etabib_db:/tmp/backup.sql

# 2. Import (Enter root password when prompted)
docker exec -i etabib_db sh -c 'export MYSQL_PWD=$MYSQL_ROOT_PASSWORD; mysql -u root etabibstore < /tmp/backup.sql'
```

### Step 3: Fix Permissions
Ensure Nginx and Django can read/write static and media files.
```bash
sudo chown -R 1000:1000 /mnt/live_data/etabib_project/static /mnt/live_data/etabib_project/media
sudo chmod -R 755 /mnt/live_data/etabib_project/static /mnt/live_data/etabib_project/media
```

---

## 7. Network & SafeLine WAF Configuration

**Objective:** Expose the application securely to the internet via SafeLine.

### 1. Box Internet (Router) Configuration
Configure **Port Forwarding (NAT)** to redirect traffic to your server (`192.168.1.65`).

| External Port | Internal IP | Internal Port | Protocol | Description |
| :--- | :--- | :--- | :--- | :--- |
| **80** | 192.168.1.65 | **80** | TCP | HTTP (SafeLine) |
| **443** | 192.168.1.65 | **443** | TCP | HTTPS (SafeLine) |
| **10000** | 192.168.1.65 | **10000** | UDP | Jitsi Video |
| **4443** | 192.168.1.65 | **4443** | TCP | Jitsi Video (Fallback) |
| **7722** | 192.168.1.65 | **7722** | TCP | SSH Admin |

*   **Firewall Level**: Set to "Low" or "Middle" (Avoid "High" blocking NAT).
*   **DMZ**: OFF.
*   **UPnP**: OFF.

### 2. SafeLine WAF Configuration
Access UI: `https://192.168.1.65:9443`

You need to create **3 separate sites** in SafeLine.

#### Site A: Main Store (`mystore.etabib.dz`)
*   **Domain**: `mystore.etabib.dz`
*   **Port**: 80 (HTTP) + **443 (HTTPS)**
*   **Upstream**: `http://192.168.1.65:8080`
    *   *Note: Use the LAN IP (192.168.1.65), NOT 127.0.0.1, as SafeLine is in a container.*

#### Site B: API (`api.etabib.dz`)
*   **Domain**: `api.etabib.dz`
*   **Port**: 80 (HTTP) + **443 (HTTPS)**
*   **Upstream**: `http://192.168.1.65:8080` (Same as Store)

#### Site C: Visio (`visio.etabib.dz`)
*   **Domain**: `visio.etabib.dz`
*   **Port**: 80 (HTTP) + **443 (HTTPS)**
*   **Upstream**: `http://192.168.1.65:8001`
    *   *Note: Jitsi Web listens on port **8001** (check your .env/compose).*

---

## 8. Troubleshooting & Maintenance

### "Bad Request (400)" Error
**Symptom:** You cannot access the site, logs show `Invalid HTTP_HOST header`.
**Solution:**
1.  Edit `.env.prod` and add the domain/IP to `ALLOWED_HOSTS`.
2.  Ensure the patched `settings.py` is present in the package directory.
3.  Restart the web container:
    ```bash
    docker compose -f docker-compose.prod.yml up -d --force-recreate web
    ```

### Updates & Quick Restart
To apply configuration changes without downtime for the DB:
```bash
docker compose -f docker-compose.prod.yml restart web celery celery-beat
```

### Viewing Logs
```bash
# Web Application Logs
docker logs -f --tail 100 etabib_web

# Database Logs
docker logs -f --tail 100 etabib_db
```

---

## 9. Automated Backups (Local 1TB HDD + Cloud FTP)

We have configured a fully automated backup system that saves data to the local 1TB HDD (`/dev/sdc5`) and uploads it to your secure FTP server.

### The Backup Script: `backup_hybrid.sh`
Located at `/mnt/live_data/etabib_project/backup_hybrid.sh`, this script:
1.  **Mounts** the 1TB HDD to `/mnt/backup_hdd`.
2.  **Dumps** the Database and **Rsyncs** Media files locally.
3.  **Uploads** encrypted backups to your FTP (`ftp.etabib.dz`) using Django's built-in tools.
4.  **Cleans up** local files older than 30 days.

### Manual Run (for testing)
```bash
sudo /mnt/live_data/etabib_project/backup_hybrid.sh
```
*Check logs at `/var/log/etabib_backup.log`*

### Automatic Scheduling (Cron)
*Prerequisite: Ensure cron is installed: `sudo apt install cron -y`*

To run this every day at 3:00 AM:
1.  Open root crontab: `sudo crontab -e`
2.  Add this line:
    ```
    0 3 * * * /mnt/live_data/etabib_project/backup_hybrid.sh
    ```

