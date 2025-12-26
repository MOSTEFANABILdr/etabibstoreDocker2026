#!/bin/bash
# backup_hybrid.sh - Created for eTabib Production
# 1. Mounts the 1TB HDD for Local Backup
# 2. Backups DB & Media to HDD
# 3. Triggers Cloud Backup (FTP) via Django

BACKUP_DIR="/mnt/backup_hdd"
HDD_DEVICE="/dev/sdc5"
LOG_FILE="/var/log/etabib_backup.log"

echo "[$(date)] Starting Hybrid Backup..." >> $LOG_FILE

# --- 1. MOUNT HDD (Backup Local) ---
# Create mount point if not exists
if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p $BACKUP_DIR
fi

# Mount if not mounted
if ! mountpoint -q $BACKUP_DIR; then
    echo "Mounting $HDD_DEVICE to $BACKUP_DIR..." >> $LOG_FILE
    mount $HDD_DEVICE $BACKUP_DIR
    if [ $? -ne 0 ]; then
        echo "ERROR: Could not mount backup drive! Exiting." >> $LOG_FILE
        exit 1
    fi
fi

# Create subfolder
LOCAL_BACKUP_PATH="$BACKUP_DIR/etabib_backups"
mkdir -p $LOCAL_BACKUP_PATH

# --- 2. LOCAL BACKUP (Fast & Secure) ---
echo "Running Local Backup to $LOCAL_BACKUP_PATH..." >> $LOG_FILE

# DB: Dump to local HDD
docker exec etabib_db mysqldump -u root -petabibstore etabibstore | gzip > "$LOCAL_BACKUP_PATH/db_$(date +%F_%H%M).sql.gz"

# MEDIA: Rsync media files to local HDD (Incremental)
mkdir -p "$LOCAL_BACKUP_PATH/media"
rsync -av /mnt/live_data/etabib_project/media/ "$LOCAL_BACKUP_PATH/media/"

# CLEANUP LOCAL: Keep last 30 days of DB dumps
find "$LOCAL_BACKUP_PATH" -name "db_*.sql.gz" -mtime +30 -delete

echo "Local Backup Completed." >> $LOG_FILE

# --- 3. CLOUD BACKUP (FTP via Django) ---
echo "Triggering Cloud Backup (FTP)..." >> $LOG_FILE

cd /mnt/live_data/etabib_project/offline_deployment_package

# DB Cloud Backup
docker compose exec -T web python manage.py dbbackup --clean
if [ $? -eq 0 ]; then
    echo "Cloud DB Backup: SUCCESS" >> $LOG_FILE
else
    echo "Cloud DB Backup: FAILED" >> $LOG_FILE
fi

# Media Cloud Backup 
# (Note: Media backup can be heavy, user policy keeps 2 active copies)
docker compose exec -T web python manage.py mediabackup --clean
if [ $? -eq 0 ]; then
    echo "Cloud Media Backup: SUCCESS" >> $LOG_FILE
else
    echo "Cloud Media Backup: FAILED" >> $LOG_FILE
fi

echo "[$(date)] Hybrid Backup Finished." >> $LOG_FILE
