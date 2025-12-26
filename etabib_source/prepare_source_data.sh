#!/bin/bash
# prepare_source_data.sh

SOURCE_SQL="/home/server/Desktop/R&D/PLACES SCRIPT/bd maps 251214.sql"
TEMP_SQL="source_data_temp.sql"

CONTAINER_NAME="etabib_db_dev"
DB_USER="etabib"
DB_PASS="etabib"
DB_NAME="etabibstore"

echo "Preparing source data..."

# Check if source file exists
if [ ! -f "$SOURCE_SQL" ]; then
    echo "Error: Source SQL file not found at $SOURCE_SQL"
    exit 1
fi

# Create a copy and replace table name
# We replace `core_contact` with `core_contact_source`
sed 's/`core_contact`/`core_contact_source`/g' "$SOURCE_SQL" > "$TEMP_SQL"

echo "Created temporary SQL file: $TEMP_SQL"

echo "Importing into database container: $CONTAINER_NAME..."

# Execute SQL in the container
cat "$TEMP_SQL" | docker exec -i "$CONTAINER_NAME" mysql -h 127.0.0.1 -u"$DB_USER" -p"$DB_PASS" "$DB_NAME"

if [ $? -eq 0 ]; then
    echo "Import successful!"
else
    echo "Import failed!"
    exit 1
fi

# Clean up temp file
rm "$TEMP_SQL"
