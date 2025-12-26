#!/bin/bash
# export_media_volume.sh
# Export media Docker volume to portable compressed archive

set -e

# Configuration
VOLUME_NAME="${1:-etabibstore_docker_media_volume_dev}"
OUTPUT_FILE="${2:-media_volume_$(date +%Y%m%d_%H%M%S).tar.gz}"

echo "========================================="
echo "Media Volume Export"
echo "========================================="
echo ""
echo "Volume: $VOLUME_NAME"
echo "Output: $OUTPUT_FILE"
echo ""

# Check if volume exists
if ! docker volume inspect $VOLUME_NAME > /dev/null 2>&1; then
    echo "Error: Volume '$VOLUME_NAME' not found"
    echo ""
    echo "Available volumes:"
    docker volume ls | grep media
    exit 1
fi

# Get volume size
echo "Analyzing volume..."
VOLUME_SIZE=$(docker run --rm -v $VOLUME_NAME:/data alpine du -sh /data | cut -f1)
FILE_COUNT=$(docker run --rm -v $VOLUME_NAME:/data alpine find /data -type f | wc -l)

echo "  Size: $VOLUME_SIZE"
echo "  Files: $FILE_COUNT"
echo ""

# Confirm export
read -p "Proceed with export? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Export cancelled."
    exit 0
fi

echo ""
echo "Exporting volume (this may take several minutes)..."
echo ""

# Export volume to compressed archive
docker run --rm \
  -v $VOLUME_NAME:/source:ro \
  -v $(pwd):/backup \
  alpine tar czf /backup/$OUTPUT_FILE -C /source .

echo ""
echo "========================================="
echo "Export Complete!"
echo "========================================="
echo ""
echo "Archive: $OUTPUT_FILE"
echo "Size: $(du -sh $OUTPUT_FILE | cut -f1)"
echo ""
echo "To deploy to production:"
echo "  1. Transfer: scp $OUTPUT_FILE user@prod-server:/tmp/"
echo "  2. Import: ./import_media_volume.sh /tmp/$OUTPUT_FILE"
echo ""
