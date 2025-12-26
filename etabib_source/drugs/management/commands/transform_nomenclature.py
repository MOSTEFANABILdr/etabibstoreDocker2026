from django.core.management.base import BaseCommand
import MySQLdb
import uuid

class Command(BaseCommand):
    help = 'Transform filtered nomenclature to medicament structure'

    def handle(self, *args, **options):
        self.stdout.write("Connecting to drug_updates DB...")
        try:
            db = MySQLdb.connect(host="etabib_db_updates", user="root", passwd="root", db="drug_updates", charset='utf8mb4')
            cursor = db.cursor(MySQLdb.cursors.DictCursor) # Use DictCursor to get column names easily
            
            # 1. Fetch Source Data
            source_table = "filtered_nomenclature_new_brands"
            self.stdout.write(f"Fetching data from {source_table}...")
            cursor.execute(f"SELECT * FROM {source_table}")
            rows = cursor.fetchall()
            
            if not rows:
                self.stdout.write(self.style.WARNING("No data found in source table."))
                return

            # Inspect columns from first row to find correct keys
            first_row = rows[0]
            keys = list(first_row.keys())
            # Helper to find key fuzzily
            def find_key(keyword):
                return next((k for k in keys if keyword in k.upper()), None)

            col_map = {
                'dci_pays': find_key('DENOMINATION_COMMUNE'),
                'num_enregistrement': find_key('ENREGISTREMENT'),
                'code': find_key('CODE'),
                'forme': find_key('FORME'),
                'dosage': find_key('DOSAGE'),
                'cond': find_key('CONDITIONNEMENT'),
                'liste': find_key('LISTE'),
                'p1': find_key('P1'),
                'p2': find_key('P2'),
                'laboratoire': find_key('LABORATOIRES_DETENTEUR'),
                'pays_labo': find_key('PAYS_DU_LABORATOIRE'),
                'type': find_key('TYPE'),
                'status': find_key('STATUT'),
                'obs': find_key('OBSERVATION')
            }
            
            self.stdout.write(f"Column Mapping: {col_map}")

            # 2. Create Target Table
            target_table = "medicament_staging"
            self.stdout.write(f"Creating {target_table}...")
            cursor.execute(f"DROP TABLE IF EXISTS {target_table}")
            
            # Schema matching drugs_medicament + original_id + mapped fields placeholders
            create_sql = f"""
                CREATE TABLE {target_table} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    unique_id VARCHAR(255) UNIQUE,
                    dci_pays VARCHAR(255),
                    dci_atc_id VARCHAR(255), -- FK placeholder
                    nom_commercial_id VARCHAR(255), -- FK placeholder
                    num_enregistrement VARCHAR(255),
                    code VARCHAR(255),
                    forme VARCHAR(255),
                    dosage VARCHAR(255),
                    cond VARCHAR(255),
                    liste VARCHAR(64),
                    p1 INT,
                    p2 INT,
                    obs VARCHAR(255),
                    laboratoire VARCHAR(255),
                    note_medecin VARCHAR(255),
                    observation VARCHAR(255),
                    type VARCHAR(30),
                    status VARCHAR(255),
                    duree_stabilitee VARCHAR(255),
                    remboursable VARCHAR(5),
                    forme_homogene_id VARCHAR(255), -- FK placeholder
                    etat INT,
                    autorise VARCHAR(5),
                    date_retrait VARCHAR(255),
                    motif_retrait TEXT,
                    categorie_id VARCHAR(255), -- FK placeholder
                    pays_labo VARCHAR(255),
                    labo_id VARCHAR(255), -- FK placeholder
                    deleted TINYINT(1) DEFAULT 0,
                    original_id INT -- Reference to filtered table
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """
            cursor.execute(create_sql)

            # 3. Transform and Insert
            self.stdout.write("Transforming and inserting data...")
            
            insert_sql = f"""
                INSERT INTO {target_table} (
                    unique_id, dci_pays, num_enregistrement, code, forme, dosage, cond, 
                    liste, p1, p2, laboratoire, pays_labo, type, status, obs, original_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values_to_insert = []
            for row in rows:
                # Generate unique_id
                uid = f'med_{uuid.uuid4().hex}'
                
                # Extract values using map
                vals = [
                    uid,
                    row.get(col_map['dci_pays']),
                    row.get(col_map['num_enregistrement']),
                    row.get(col_map['code']),
                    row.get(col_map['forme']),
                    row.get(col_map['dosage']),
                    row.get(col_map['cond']),
                    row.get(col_map['liste']),
                    row.get(col_map['p1']),
                    row.get(col_map['p2']),
                    row.get(col_map['laboratoire']),
                    row.get(col_map['pays_labo']),
                    row.get(col_map['type']),
                    row.get(col_map['status']),
                    row.get(col_map['obs']),
                    row.get('id') # original_id
                ]
                
                # Clean None/NaN values for string fields?
                # MySQL handles None as NULL, which is fine for nullable fields.
                # Just ensure P1/P2 are integers or None
                try:
                    vals[8] = int(float(vals[8])) if vals[8] is not None and vals[8] != '' else None # p1
                except:
                    vals[8] = None
                    
                try:
                    vals[9] = int(float(vals[9])) if vals[9] is not None and vals[9] != '' else None # p2
                except:
                    vals[9] = None

                values_to_insert.append(vals)

            # Batch insert
            batch_size = 1000
            for i in range(0, len(values_to_insert), batch_size):
                batch = values_to_insert[i:i+batch_size]
                cursor.executemany(insert_sql, batch)
                self.stdout.write(f"Inserted {min(i+batch_size, len(values_to_insert))}/{len(values_to_insert)} rows...")

            db.commit()
            cursor.close()
            db.close()
            self.stdout.write(self.style.SUCCESS("Transformation complete."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
