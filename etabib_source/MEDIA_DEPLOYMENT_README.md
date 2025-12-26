# Media Deployment - Quick Reference

## 📦 Production Media Archive

**File**: `media_volume_production.tar.gz`  
**Size**: ~4.4GB (compressed)  
**Contents**: 4,658 media files (avatars, documents, images, etc.)  
**Created**: 2024-12-14

---

## 🚀 Quick Deployment to Production

### 1. Transfer Archive to Production Server
```bash
scp media_volume_production.tar.gz user@production-server:/tmp/
```

### 2. Import on Production Server
```bash
ssh user@production-server
cd /opt/etabibstore
./import_media_volume.sh /tmp/media_volume_production.tar.gz
```

### 3. Start Production Services
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 4. Verify
```bash
docker-compose exec web ls -la /app/media/ | head -20
```

---

## 📚 Full Documentation

For complete instructions, troubleshooting, and best practices, see:
- **[MEDIA_DEPLOYMENT_GUIDE.md](./MEDIA_DEPLOYMENT_GUIDE.md)** - Complete deployment guide
- **[PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md)** - Full production deployment

---

## 🔧 Useful Commands

### Export Media Volume (if needed)
```bash
./export_media_volume.sh etabibstore_docker_media_volume_dev media_volume_new.tar.gz
```

### Check Volume Size
```bash
docker run --rm -v etabibstore_media_volume_prod:/data alpine du -sh /data
```

### Backup Production Media
```bash
docker run --rm \
  -v etabibstore_media_volume_prod:/source:ro \
  -v $(pwd):/backup \
  alpine tar czf /backup/media_backup_$(date +%Y%m%d).tar.gz -C /source .
```

---

## ⚠️ Important Notes

1. **Always backup** before updating production media
2. **Test in staging** before production deployment
3. **Verify disk space** before importing (need ~10GB free)
4. **Check permissions** after import if media doesn't load

---

## 📞 Need Help?

1. Check [MEDIA_DEPLOYMENT_GUIDE.md](./MEDIA_DEPLOYMENT_GUIDE.md)
2. Review docker-compose.prod.yml configuration
3. Check logs: `docker-compose logs web nginx`
4. Contact development team

---

**Scripts Available:**
- `export_media_volume.sh` - Export volume to archive
- `import_media_volume.sh` - Import archive to volume
- `deploy_media_to_production.sh` - Alternative deployment method
