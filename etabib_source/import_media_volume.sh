#!/bin/bash
# import_media_volume.sh
# Import media from compressed archive into Docker volume

set -e

# Configuration
ARCHIVE_FILE="${1}"
VOLUME_NAME="${2:-etabibstore_media_volume_prod}"

echo "========================================="
echo "Media Volume Import"
echo "========================================="
echo ""

# Validate archive file
if [ -z "$ARCHIVE_FILE" ]; then
    echo "Usage: $0 <archive_file> [volume_name]"
    echo ""
    echo "Example:"
    echo "  $0 media_volume_20241214.tar.gz"
    echo "  $0 /tmp/media_volume.tar.gz etabibstore_media_volume_prod"
    exit 1
fi

if [ ! -f "$ARCHIVE_FILE" ]; then
    echo "Error: Archive file not found: $ARCHIVE_FILE"
    exit 1
fi

echo "Archive: $ARCHIVE_FILE"
echo "Archive size: $(du -sh $ARCHIVE_FILE | cut -f1)"
echo "Target volume: $VOLUME_NAME"
echo ""

# Check if volume exists
if docker volume inspect $VOLUME_NAME > /dev/null 2>&1; then
    echo "Warning: Volume '$VOLUME_NAME' already exists"
    read -p "Overwrite existing volume? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Import cancelled."
        exit 0
    fi
    echo "Removing existing volume..."
    docker volume rm $VOLUME_NAME || true
fi

# Create volume
echo "Creating volume: $VOLUME_NAME"
docker volume create $VOLUME_NAME

echo ""
echo "Importing media (this may take several minutes)..."
echo ""

# Import archive to volume
docker run --rm \
  -v $VOLUME_NAME:/target \
  -v $(dirname $(realpath $ARCHIVE_FILE)):/backup \
  alpine tar xzf /backup/$(basename $ARCHIVE_FILE) -C /target

echo ""
echo "========================================="
echo "Import Complete!"
echo "========================================="
echo ""

# Verify import
VOLUME_SIZE=$(docker run --rm -v $VOLUME_NAME:/data alpine du -sh /data | cut -f1)
FILE_COUNT=$(docker run --rm -v $VOLUME_NAME:/data alpine find /data -type f | wc -l)

echo "Volume: $VOLUME_NAME"
echo "  Size: $VOLUME_SIZE"
echo "  Files: $FILE_COUNT"
echo ""
echo "Volume is ready to use in docker-compose.yml"
echo ""
