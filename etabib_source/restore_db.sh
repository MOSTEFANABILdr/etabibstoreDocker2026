#!/bin/bash

# Check if a directory argument is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_sql_directory>"
    exit 1
fi

SQL_DIR="$1"

# Check if the directory exists
if [ ! -d "$SQL_DIR" ]; then
    echo "Error: Directory '$SQL_DIR' not found."
    exit 1
fi

CONTAINER_NAME="etabib_db_dev"
DB_USER="etabib"
DB_PASS="etabib"
DB_NAME="etabibstore"

echo "Starting database restoration from '$SQL_DIR'..."

# Function to execute SQL in the container
exec_sql() {
    docker exec -i "$CONTAINER_NAME" mysql -h 127.0.0.1 -u"$DB_USER" -p"$DB_PASS" "$DB_NAME"
}

# Disable Foreign Key Checks
echo "SET FOREIGN_KEY_CHECKS=0;" | exec_sql

# 1. Import Structure
STRUCTURE_FILE=$(find "$SQL_DIR" -name "*structure_only*.sql" | head -n 1)
if [ -n "$STRUCTURE_FILE" ]; then
    echo "Importing structure from $STRUCTURE_FILE..."
    cat "$STRUCTURE_FILE" | exec_sql
else
    echo "Warning: No structure file found (looking for *structure_only*.sql)."
fi

# 2. Import Data (all other files except structure and routines)
echo "Importing data files..."
find "$SQL_DIR" -name "*.sql" ! -name "*structure_only*.sql" ! -name "*routines.sql" -print0 | while IFS= read -r -d '' file; do
    echo "Importing $file..."
    cat "$file" | exec_sql
done

# 3. Import Routines
ROUTINES_FILE=$(find "$SQL_DIR" -name "*routines.sql" | head -n 1)
if [ -n "$ROUTINES_FILE" ]; then
    echo "Importing routines from $ROUTINES_FILE..."
    cat "$ROUTINES_FILE" | exec_sql
fi

# Enable Foreign Key Checks
echo "SET FOREIGN_KEY_CHECKS=1;" | exec_sql

echo "Database restoration completed."
