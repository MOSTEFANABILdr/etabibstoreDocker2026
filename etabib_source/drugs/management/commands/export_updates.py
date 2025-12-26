from django.core.management.base import BaseCommand
from drugs.models import Medicament, DciAtc, NomCommercial
import pandas as pd
import MySQLdb
import os

class Command(BaseCommand):
    help = 'Export drug updates to separate MySQL database'

    def handle(self, *args, **options):
        file_path = '/app/drugs/updates_official/NOMENCLATURE-VERSION-NOVEMBRE-2025.xlsx'
        
        # Connect to the update DB
        try:
            db = MySQLdb.connect(
                host="etabib_db_updates",
                user="root",
                passwd="root",
                db="drug_updates",
                charset='utf8mb4'
            )
            cursor = db.cursor()
            self.stdout.write(self.style.SUCCESS("Connected to drug_updates database."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to connect to update DB: {e}"))
            return

        # Create Tables
        self.create_tables(cursor)
        
        # Analyze and Insert
        try:
            xl = pd.ExcelFile(file_path)
            self.stdout.write(f"Sheets found: {xl.sheet_names}")
            
            # Find Nomenclature sheet
            nomenclature_sheet = next((s for s in xl.sheet_names if 'nomenclature' in s.lower()), None)
            
            if nomenclature_sheet:
                self.stdout.write(f"Processing {nomenclature_sheet}...")
                df = xl.parse(nomenclature_sheet)
                self.process_sheet(df, cursor, is_retrait=False)
            else:
                self.stdout.write("Sheet 'Nomenclature' not found!")
            
            if 'Retraits' in xl.sheet_names:
                self.stdout.write("Processing Retraits...")
                df_retrait = xl.parse('Retraits')
                self.process_sheet(df_retrait, cursor, is_retrait=True)
            else:
                self.stdout.write("Sheet 'Retraits' not found!")

            db.commit()
            self.stdout.write(self.style.SUCCESS("Export complete."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error processing file: {e}"))
            db.rollback()
        finally:
            cursor.close()
            db.close()

    def create_tables(self, cursor):
        # Drop tables to ensure clean state and correct charset
        cursor.execute("DROP TABLE IF EXISTS updates")
        cursor.execute("DROP TABLE IF EXISTS new_drugs")
        cursor.execute("DROP TABLE IF EXISTS new_brands")
        cursor.execute("DROP TABLE IF EXISTS new_dcis")

        queries = [
            """
            CREATE TABLE new_dcis (
                id INT AUTO_INCREMENT PRIMARY KEY,
                designation VARCHAR(255) UNIQUE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE new_brands (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) UNIQUE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE new_drugs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                reg_num VARCHAR(255),
                dci VARCHAR(500),
                brand VARCHAR(500),
                forme VARCHAR(500),
                dosage VARCHAR(500),
                cond TEXT,
                laboratoire VARCHAR(500),
                pays VARCHAR(500)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE updates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                drug_id INT,
                reg_num VARCHAR(255),
                update_type VARCHAR(50),
                field VARCHAR(50),
                old_value TEXT,
                new_value TEXT
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """
        ]
        for q in queries:
            cursor.execute(q)

    def process_sheet(self, df, cursor, is_retrait):
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        new_drugs_count = 0
        updates_count = 0
        
        for index, row in df.iterrows():
            reg_num = str(row.get('N°ENREGISTREMENT', '')).strip()
            dci_name = str(row.get('DENOMINATION COMMUNE INTERNATIONALE', '')).strip()
            brand_name = str(row.get('NOM DE MARQUE', '')).strip()
            forme = str(row.get('FORME', '')).strip()
            dosage = str(row.get('DOSAGE', '')).strip()
            cond = str(row.get('CONDITIONNEMENT', '')).strip()
            
            # Find existing
            medicament = None
            if reg_num and reg_num != 'nan':
                medicament = Medicament.objects.filter(num_enregistrement=reg_num).first()
            
            if not medicament:
                dci_obj = DciAtc.objects.filter(designation_fr__iexact=dci_name).first()
                brand_obj = NomCommercial.objects.filter(nom_fr__iexact=brand_name).first()
                if dci_obj and brand_obj:
                    qs = Medicament.objects.filter(
                        dci_atc=dci_obj,
                        nom_commercial=brand_obj,
                        forme__iexact=forme,
                        dosage__iexact=dosage
                    )
                    medicament = qs.first()

            if medicament:
                # UPDATES
                if is_retrait:
                    date_retrait = str(row.get('DATE DE RETRAIT', '')).strip()
                    motif_retrait = str(row.get('MOTIF DE RETRAIT', '')).strip()
                    
                    if medicament.date_retrait != date_retrait:
                        self.insert_update(cursor, medicament.id, reg_num, 'retrait', 'date_retrait', medicament.date_retrait, date_retrait)
                        updates_count += 1
                    if medicament.motif_retrait != motif_retrait:
                        self.insert_update(cursor, medicament.id, reg_num, 'retrait', 'motif_retrait', medicament.motif_retrait, motif_retrait)
                        updates_count += 1
                else:
                    new_status = str(row.get('STATUT', '')).strip()
                    if new_status and new_status != 'nan' and medicament.status != new_status:
                        self.insert_update(cursor, medicament.id, reg_num, 'status', 'status', medicament.status, new_status)
                        updates_count += 1
            else:
                # NEW DRUG
                if not is_retrait: # Only add new drugs from Nomenclature
                    new_drugs_count += 1
                    
                    # Check/Insert DCI
                    if not DciAtc.objects.filter(designation_fr__iexact=dci_name).exists():
                        cursor.execute("INSERT IGNORE INTO new_dcis (designation) VALUES (%s)", [dci_name])
                    
                    # Check/Insert Brand
                    if not NomCommercial.objects.filter(nom_fr__iexact=brand_name).exists():
                        cursor.execute("INSERT IGNORE INTO new_brands (name) VALUES (%s)", [brand_name])
                        
                    # Insert Drug
                    cursor.execute("""
                        INSERT INTO new_drugs (reg_num, dci, brand, forme, dosage, cond, laboratoire, pays)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, [
                        reg_num, dci_name, brand_name, forme, dosage, cond,
                        str(row.get("LABORATOIRES DETENTEUR DE LA DECISION D'ENREGISTREMENT", '')).strip(),
                        str(row.get("PAYS DU LABORATOIRE DETENTEUR DE LA DECISION D'ENREGISTREMENT", '')).strip()
                    ])
        
        self.stdout.write(f"Processed sheet (Retrait={is_retrait}): {new_drugs_count} new drugs, {updates_count} updates.")

    def insert_update(self, cursor, drug_id, reg_num, up_type, field, old, new):
        cursor.execute("""
            INSERT INTO updates (drug_id, reg_num, update_type, field, old_value, new_value)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, [drug_id, reg_num, up_type, field, old, new])
