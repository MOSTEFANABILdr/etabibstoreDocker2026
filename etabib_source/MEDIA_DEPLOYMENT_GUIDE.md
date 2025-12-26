# Media Volume Deployment Guide for Developers

## Overview
This guide explains how to deploy the Etabibstore media files to production using Docker volumes. The media is packaged as a portable Docker volume archive that can be easily transferred and imported on any server.

## What is the Media Volume?

The media volume contains all user-uploaded files, images, documents, and assets:
- User avatars and profile pictures
- Medical certificates and documents
- Product images and catalogs
- Announcements and banners
- Cache files
- **Total size**: ~4.5GB (4,658 files)

## Prerequisites

### On Your Local Machine
- Docker and Docker Compose installed
- Access to the project repository
- Sufficient disk space (~10GB for export)

### On Production Server
- Docker and Docker Compose installed
- SSH access with appropriate permissions
- Sufficient disk space (~10GB)
- Network connectivity to transfer files

## Deployment Methods

### Method 1: Using Pre-built Archive (Recommended)

This is the fastest method if you have the pre-exported archive.

#### Step 1: Locate the Media Archive

The media archive is located at:
```
/home/server/PycharmProjects/etabibstore_docker/media_volume_production.tar.gz
```

Size: ~2-3GB (compressed)

#### Step 2: Transfer to Production Server

```bash
# Transfer via SCP
scp media_volume_production.tar.gz user@production-server:/tmp/

# Or via rsync (resumable)
rsync -avz --progress media_volume_production.tar.gz user@production-server:/tmp/
```

#### Step 3: Import on Production Server

```bash
# SSH to production server
ssh user@production-server

# Navigate to application directory
cd /opt/etabibstore

# Import the media volume
./import_media_volume.sh /tmp/media_volume_production.tar.gz

# Verify import
docker run --rm -v etabibstore_media_volume_prod:/data alpine ls -la /data | head -20
```

#### Step 4: Start Production Services

```bash
# Update docker-compose.prod.yml if needed (should already be configured)
docker-compose -f docker-compose.prod.yml up -d

# Verify media is accessible
docker-compose -f docker-compose.prod.yml exec web ls -la /app/media/ | head -20
```

---

### Method 2: Export from Dev and Import to Prod

Use this method if you need to create a fresh export from your development environment.

#### Step 1: Export Media Volume from Dev

```bash
# On your local development machine
cd /home/server/PycharmProjects/etabibstore_docker

# Export the dev media volume
./export_media_volume.sh etabibstore_docker_media_volume_dev media_volume_production.tar.gz

# This creates: media_volume_production.tar.gz (~2-3GB)
```

#### Step 2: Transfer and Import (same as Method 1, Steps 2-4)

---

### Method 3: Direct Volume Sync (Advanced)

For advanced users who want to sync volumes directly between servers.

```bash
# Export from dev
docker run --rm \
  -v etabibstore_docker_media_volume_dev:/source:ro \
  -v $(pwd):/backup \
  alpine tar czf /backup/media.tar.gz -C /source .

# Transfer
scp media.tar.gz user@prod:/tmp/

# Import on prod
ssh user@prod
docker volume create etabibstore_media_volume_prod
docker run --rm \
  -v etabibstore_media_volume_prod:/target \
  -v /tmp:/backup \
  alpine tar xzf /backup/media.tar.gz -C /target
```

---

## Verification Checklist

After deploying media to production, verify:

### 1. Volume Exists
```bash
docker volume ls | grep media
# Should show: etabibstore_media_volume_prod
```

### 2. File Count and Size
```bash
docker run --rm -v etabibstore_media_volume_prod:/data alpine sh -c "find /data -type f | wc -l && du -sh /data"
# Expected: 4658 files, ~4.5G
```

### 3. Container Access
```bash
docker-compose -f docker-compose.prod.yml exec web ls -la /app/media/
# Should list directories: action, annonce, avatar, cartes, etc.
```

### 4. Web Access
- Navigate to your application URL
- Check user profiles (avatars should load)
- Check product pages (images should display)
- Upload a test file to verify write permissions

### 5. Nginx/Web Server
```bash
# Test media serving
curl -I https://your-domain.com/media/default_card.png
# Should return: HTTP/1.1 200 OK
```

---

## Updating Media in Production

### Option A: Full Re-import
If you have significant media changes:

```bash
# 1. Export new media from dev
./export_media_volume.sh etabibstore_docker_media_volume_dev media_volume_updated.tar.gz

# 2. Transfer to production
scp media_volume_updated.tar.gz user@prod:/tmp/

# 3. Stop services
ssh user@prod
cd /opt/etabibstore
docker-compose -f docker-compose.prod.yml down

# 4. Backup existing volume
docker run --rm \
  -v etabibstore_media_volume_prod:/source:ro \
  -v /opt/backups:/backup \
  alpine tar czf /backup/media_backup_$(date +%Y%m%d).tar.gz -C /source .

# 5. Import new media
./import_media_volume.sh /tmp/media_volume_updated.tar.gz etabibstore_media_volume_prod

# 6. Restart services
docker-compose -f docker-compose.prod.yml up -d
```

### Option B: Incremental Sync
For small updates:

```bash
# Sync specific directories
rsync -avz ./media/uploads/ user@prod:/opt/etabibstore/media/uploads/

# Or use docker cp for specific files
docker cp ./media/new_image.jpg etabib_web:/app/media/
```

---

## Troubleshooting

### Issue: "Volume not found" error

**Solution:**
```bash
# List all volumes
docker volume ls

# Create volume if missing
docker volume create etabibstore_media_volume_prod
```

### Issue: Permission denied errors

**Solution:**
```bash
# Fix permissions inside volume
docker run --rm -v etabibstore_media_volume_prod:/data alpine chmod -R 755 /data
docker run --rm -v etabibstore_media_volume_prod:/data alpine chown -R 1000:1000 /data
```

### Issue: Media files not loading in browser

**Checklist:**
1. Verify volume is mounted in docker-compose.prod.yml
2. Check nginx configuration for /media/ location
3. Verify file permissions (755 for directories, 644 for files)
4. Check browser console for 404 errors
5. Verify MEDIA_URL and MEDIA_ROOT in Django settings

**Debug commands:**
```bash
# Check if file exists in container
docker-compose exec web ls -la /app/media/path/to/file.jpg

# Check nginx logs
docker-compose logs nginx | grep media

# Test direct file access
docker-compose exec web cat /app/media/default_card.png > /dev/null && echo "File readable"
```

### Issue: Out of disk space

**Solution:**
```bash
# Check disk usage
df -h

# Clean up old Docker volumes
docker volume prune

# Remove old images
docker image prune -a
```

### Issue: Slow transfer to production

**Solutions:**
1. Use rsync instead of scp (supports resume)
2. Compress with higher compression: `tar czf` → `tar cJf` (xz compression)
3. Transfer during off-peak hours
4. Use screen/tmux for long transfers
5. Consider using a CDN or object storage for media

---

## Best Practices

### 1. Always Backup Before Updates
```bash
# Backup production media volume
docker run --rm \
  -v etabibstore_media_volume_prod:/source:ro \
  -v /opt/backups:/backup \
  alpine tar czf /backup/media_backup_$(date +%Y%m%d).tar.gz -C /source .
```

### 2. Version Your Media Archives
```bash
# Use dated filenames
media_volume_production_20241214.tar.gz
media_volume_production_20241220.tar.gz
```

### 3. Test in Staging First
- Import media to staging environment
- Test thoroughly
- Then deploy to production

### 4. Monitor Disk Usage
```bash
# Set up monitoring for volume size
docker run --rm -v etabibstore_media_volume_prod:/data alpine du -sh /data
```

### 5. Regular Backups
```bash
# Add to cron (daily backup)
0 2 * * * docker run --rm -v etabibstore_media_volume_prod:/source:ro -v /opt/backups:/backup alpine tar czf /backup/media_backup_$(date +\%Y\%m\%d).tar.gz -C /source .
```

---

## Quick Reference Commands

### Export Media Volume
```bash
./export_media_volume.sh [volume_name] [output_file]
```

### Import Media Volume
```bash
./import_media_volume.sh <archive_file> [volume_name]
```

### List Volumes
```bash
docker volume ls | grep media
```

### Inspect Volume
```bash
docker volume inspect etabibstore_media_volume_prod
```

### Remove Volume (DANGEROUS)
```bash
docker volume rm etabibstore_media_volume_prod
```

### Backup Volume
```bash
docker run --rm -v etabibstore_media_volume_prod:/source:ro -v $(pwd):/backup alpine tar czf /backup/media_backup.tar.gz -C /source .
```

---

## Support and Contact

For issues or questions:
1. Check this documentation
2. Review docker-compose.prod.yml configuration
3. Check application logs: `docker-compose logs web`
4. Contact the development team

---

## Appendix: Docker Compose Configuration

### Production docker-compose.yml Media Configuration

```yaml
services:
  web:
    volumes:
      - media_volume:/app/media
  
  nginx:
    volumes:
      - media_volume:/app/media

volumes:
  media_volume:
    name: etabibstore_media_volume_prod
```

This ensures:
- Consistent volume naming
- Shared access between web and nginx
- Persistent storage across container restarts

---

**Last Updated**: 2024-12-14  
**Version**: 1.0  
**Maintainer**: Development Team
