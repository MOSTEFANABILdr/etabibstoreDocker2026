from django.core.management.base import BaseCommand
import MySQLdb
import uuid

class Command(BaseCommand):
    help = 'Stage new brands and link to medicament_staging'

    def handle(self, *args, **options):
        self.stdout.write("Connecting to drug_updates DB...")
        try:
            db = MySQLdb.connect(host="etabib_db_updates", user="root", passwd="root", db="drug_updates", charset='utf8mb4')
            cursor = db.cursor()

            # 1. Create NomCommercial Staging Table
            self.stdout.write("Creating nom_commercial_staging table...")
            cursor.execute("DROP TABLE IF EXISTS nom_commercial_staging")
            cursor.execute("""
                CREATE TABLE nom_commercial_staging (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    unique_id VARCHAR(255) UNIQUE,
                    nom_fr VARCHAR(255),
                    deleted TINYINT(1) DEFAULT 0
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)

            # 2. Identify Unique New Brands
            # We can get them from brand_dci_mapping_staging OR filtered_nomenclature_new_brands
            # filtered_nomenclature_new_brands is the source for medicament_staging, so let's use that to be consistent.
            # The column name is likely NOM_DE_MARQUE (sanitized)
            
            self.stdout.write("Fetching distinct brands from filtered_nomenclature_new_brands...")
            cursor.execute("SELECT DISTINCT NOM_DE_MARQUE FROM filtered_nomenclature_new_brands")
            brands = cursor.fetchall()
            
            self.stdout.write(f"Found {len(brands)} distinct brands.")

            # 3. Insert into Staging
            self.stdout.write("Inserting brands into staging...")
            insert_sql = "INSERT INTO nom_commercial_staging (unique_id, nom_fr) VALUES (%s, %s)"
            
            values = []
            for (brand_name,) in brands:
                if brand_name:
                    uid = f"nc_{uuid.uuid4().hex}"
                    values.append((uid, brand_name))
            
            cursor.executemany(insert_sql, values)
            self.stdout.write(f"Inserted {len(values)} brands.")

            # 4. Link Medicaments
            self.stdout.write("Linking medicament_staging to nom_commercial_staging...")
            # Update medicament_staging.nom_commercial_id
            # Join via original_id -> filtered_nomenclature -> NOM_DE_MARQUE -> nom_commercial_staging
            
            update_sql = """
                UPDATE medicament_staging ms
                JOIN filtered_nomenclature_new_brands f ON ms.original_id = f.id
                JOIN nom_commercial_staging ncs ON f.NOM_DE_MARQUE = ncs.nom_fr
                SET ms.nom_commercial_id = ncs.unique_id
            """
            cursor.execute(update_sql)
            self.stdout.write(f"Updated {cursor.rowcount} rows in medicament_staging.")

            db.commit()
            cursor.close()
            db.close()
            self.stdout.write(self.style.SUCCESS("Brand staging and linking complete."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
