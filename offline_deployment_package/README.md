# Production Deployment Guide: eTabib Solution

This guide provides step-by-step instructions for deploying the eTabib solution (Django + Jitsi) on a self-hosted production server.

## Server Specifications
- **CPU**: Core i5
- **RAM**: 16GB
- **Storage**: SSD (2 partitions) + HDDs (Cold storage/Backup)
- **OS**: Ubuntu Server 24.04 LTS
- **Network**: Behind an internet box (NAT)

---

## 1. Preparing Deployment (From your Dev Machine)

Before going to the server, you must package everything on your development machine.

1. **Run the Preparation Script**:
   Run the `prepare_offline_deployment.sh` script. It will create a folder named `offline_deployment_package` containing:
   - All software components (Docker images).
   - Your current database data.
   - All media files (photos, documents).
   - Configuration files.

2. **Transfer to USB/External Drive**:
   Copy the entire `offline_deployment_package` folder to an external drive to take it to the production server.

---

## 2. Initial Server Setup & Partitioning

### OS Installation
1. Install **Ubuntu Server 24.04 LTS**.
2. During installation, create a small partition (e.g., 100GB) for the system (`/`) on the SSD.
3. Leave the rest of the SSD unformatted or create a second partition for **Live Data**.

### Partitioning the SSD for Live Data
After installation, identify your second partition (e.g., `/dev/sda2`) and mount it to `/mnt/live_data`.

```bash
# 1. Identify the partition (look for the one with the largest size on your SSD)
lsblk

# 2. Format the second partition (WARNING: This erases data on that partition)
# Replace /dev/sda2 with your actual partition name from the previous step
sudo mkfs.ext4 /dev/sda2

# 3. Create a permanent home for your data
sudo mkdir -p /mnt/live_data

# 4. Get the unique ID (UUID) of the partition
sudo blkid /dev/sda2

# 5. Make it permanent: Add to /etc/fstab so it mounts every time the server starts
# Copy the UUID from the previous step and add this line to the end of the file:
# UUID=your-uuid-here /mnt/live_data ext4 defaults 0 2
sudo nano /etc/fstab

# 6. Mount it now
sudo mount -a

# 7. Create folders for the project
sudo mkdir -p /mnt/live_data/etabib_project
sudo chown -R $USER:$USER /mnt/live_data/etabib_project
```

### Configuring HDDs for Cold Storage
Mount your HDDs to `/mnt/backup` using the same method as above. This is where you will store your weekly backups.

---

## 3. Security Hardening (Essential)

### Secure SSH Access
1. **Disable Password Authentication**: This prevents hackers from guessing your password. You must use SSH keys.
2. **Change Default Port**: Move SSH from 22 to a custom port (e.g., 2222) to avoid automated bots.

```bash
# Edit SSH config
sudo nano /etc/ssh/sshd_config

# Find and change these lines:
# Port 2222
# PasswordAuthentication no
# PermitRootLogin no

# Restart SSH to apply changes
sudo systemctl restart ssh
```

### Firewall (UFW)
The firewall blocks all traffic except what you explicitly allow.

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 2222/tcp   # SSH
sudo ufw allow 80/tcp     # Web (HTTP)
sudo ufw allow 443/tcp    # Web (HTTPS)
sudo ufw allow 10000/udp  # Jitsi Video
sudo ufw allow 4443/tcp   # Jitsi Data
sudo ufw enable
```

---

## 4. Docker Installation (Offline Friendly)

If the server has no internet, you must pre-download the Docker `.deb` packages on a machine with internet and transfer them via USB.

### Standard Installation (If internet is available)
```bash
sudo apt update
sudo apt install docker.io docker-compose-v2 -y
sudo usermod -aG docker $USER
# Log out and log back in for this to take effect
```

---

## 5. Deployment on Production Server

### Step 1: Transfer Files
Transfer the `offline_deployment_package` folder from your USB drive to `/mnt/live_data/etabib_project/` on the server.

### Step 2: Load Docker Images
This installs the software components without needing the internet.
```bash
cd /mnt/live_data/etabib_project/offline_deployment_package
gunzip -c etabib_images.tar.gz | docker load
gunzip -c jitsi_images.tar.gz | docker load
```

### Step 3: Configure Volumes to use the 2nd Partition
Your `docker-compose.prod.yml` should point to the SSD's 2nd partition for all data storage.

```yaml
# Example snippet from docker-compose.prod.yml
services:
  db:
    volumes:
      - /mnt/live_data/etabib_project/mysql_data:/var/lib/mysql
  web:
    volumes:
      - /mnt/live_data/etabib_project/media:/app/media
      - /mnt/live_data/etabib_project/static:/app/static
```

### Step 4: Launch the System
```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.jitsi.yml up -d
```

### Step 5: Restore your Data
This imports all your existing patients, doctors, and records.
```bash
cat etabibstore_backup.sql | docker exec -i etabib_db_prod mysql -u root -p etabibstore
```

---

## 6. Performance Optimization

1. **MySQL Tuning**: Since you have 16GB RAM, we dedicate 8GB to the database for speed.
2. **SSD Optimization**: We use the 2nd partition for "Live Data" to ensure high-speed access for the database and media files.
3. **Log Rotation**: We limit log sizes to 10MB to avoid filling up the SSD over time.

---

## 7. Maintenance & Backups
To backup your data to the HDDs:
```bash
# Run this weekly
docker exec etabib_db_prod mysqldump -u root -p etabibstore > /mnt/backup/db_$(date +%F).sql
tar -czf /mnt/backup/media_$(date +%F).tar.gz /mnt/live_data/etabib_project/media
```
