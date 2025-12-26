#!/bin/bash
# deploy_media_to_production.sh
# Script to deploy media files to production server

set -e  # Exit on error

# Configuration
PROD_SERVER="your-production-server"  # Replace with actual server
PROD_USER="your-username"              # Replace with actual username
PROD_PATH="/path/to/production/etabibWebsite/media"  # Replace with actual path
LOCAL_MEDIA="./media"

echo "========================================="
echo "Media Deployment to Production Server"
echo "========================================="
echo ""

# Check if local media exists
if [ ! -d "$LOCAL_MEDIA" ]; then
    echo "Error: Local media directory not found: $LOCAL_MEDIA"
    exit 1
fi

# Display media stats
echo "Local media statistics:"
echo "  Size: $(du -sh $LOCAL_MEDIA | cut -f1)"
echo "  Files: $(find $LOCAL_MEDIA -type f | wc -l)"
echo ""

# Confirm deployment
read -p "Deploy to $PROD_SERVER:$PROD_PATH? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "Starting deployment..."
echo ""

# Option 1: Direct rsync to production server
echo "Method 1: Direct rsync (recommended)"
echo "Command:"
echo "  rsync -avz --progress $LOCAL_MEDIA/ $PROD_USER@$PROD_SERVER:$PROD_PATH/"
echo ""

# Option 2: Create compressed archive for manual transfer
echo "Method 2: Create compressed archive"
echo "Creating media archive..."
tar -czf media_production_$(date +%Y%m%d_%H%M%S).tar.gz -C . media/
echo "Archive created: media_production_$(date +%Y%m%d_%H%M%S).tar.gz"
echo ""
echo "To deploy manually:"
echo "  1. Upload: scp media_production_*.tar.gz $PROD_USER@$PROD_SERVER:/tmp/"
echo "  2. SSH to server: ssh $PROD_USER@$PROD_SERVER"
echo "  3. Extract: cd /path/to/production/etabibWebsite && tar -xzf /tmp/media_production_*.tar.gz"
echo "  4. Fix permissions: chown -R www-data:www-data media/ && chmod -R 755 media/"
echo ""

# Option 3: Docker volume deployment
echo "Method 3: Docker volume deployment (if using Docker on production)"
echo "  1. Copy media to production server"
echo "  2. Update docker-compose.prod.yml to mount media directory"
echo "  3. Restart containers: docker-compose -f docker-compose.prod.yml restart web"
echo ""

echo "========================================="
echo "Deployment script completed"
echo "========================================="
