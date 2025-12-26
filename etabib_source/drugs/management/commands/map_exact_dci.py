from django.core.management.base import BaseCommand
from drugs.models import DciAtc
import MySQLdb

class Command(BaseCommand):
    help = 'Map exact DCI matches in medicament_staging'

    def handle(self, *args, **options):
        # 1. Fetch Existing DCIs
        self.stdout.write("Fetching existing DCIs...")
        existing_dcis = list(DciAtc.objects.filter(deleted=False).values('unique_id', 'designation_fr'))
        
        # Create a lookup map: Normalized Designation -> Unique ID
        dci_map = {}
        for dci in existing_dcis:
            name = dci['designation_fr']
            if name:
                norm_name = name.strip().upper()
                dci_map[norm_name] = dci['unique_id']
        
        self.stdout.write(f"Loaded {len(dci_map)} unique existing DCIs.")

        # 2. Connect to Staging DB
        self.stdout.write("Connecting to drug_updates DB...")
        try:
            db = MySQLdb.connect(host="etabib_db_updates", user="root", passwd="root", db="drug_updates", charset='utf8mb4')
            cursor = db.cursor(MySQLdb.cursors.DictCursor)
            
            # 3. Fetch Staging Data (where dci_atc_id is NULL)
            cursor.execute("SELECT id, dci_pays FROM medicament_staging WHERE dci_atc_id IS NULL OR dci_atc_id = ''")
            rows = cursor.fetchall()
            self.stdout.write(f"Found {len(rows)} rows to process.")
            
            updates = []
            matched_count = 0
            
            for row in rows:
                dci_pays = row['dci_pays']
                if not dci_pays:
                    continue
                
                norm_dci = dci_pays.strip().upper()
                
                if norm_dci in dci_map:
                    matched_id = dci_map[norm_dci]
                    updates.append((matched_id, row['id']))
                    matched_count += 1
            
            # 4. Update DB
            if updates:
                self.stdout.write(f"Updating {len(updates)} rows...")
                update_sql = "UPDATE medicament_staging SET dci_atc_id = %s WHERE id = %s"
                
                # Batch update
                batch_size = 1000
                for i in range(0, len(updates), batch_size):
                    batch = updates[i:i+batch_size]
                    cursor.executemany(update_sql, batch)
                    self.stdout.write(f"Updated {min(i+batch_size, len(updates))}/{len(updates)} rows...")
                
                db.commit()
                self.stdout.write(self.style.SUCCESS(f"Successfully mapped {matched_count} exact matches."))
            else:
                self.stdout.write("No exact matches found.")

            cursor.close()
            db.close()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
