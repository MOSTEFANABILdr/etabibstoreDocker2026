import pandas as pd
import uuid
from django.core.management.base import BaseCommand
from drugs.models import NomCommercial
import MySQLdb

class Command(BaseCommand):
    help = 'Import missing new brands from other sheets'

    def handle(self, *args, **options):
        file_path = '/app/drugs/updates_official/NOMENCLATURE-VERSION-NOVEMBRE-2025.xlsx'
        
        # 1. Fetch Existing Brands (Main DB)
        existing_brands = set(NomCommercial.objects.filter(deleted=False).values_list('nom_fr', flat=True))
        existing_brands_norm = {b.strip().upper() for b in existing_brands if b}
        
        # 2. Fetch Staged Brands (to avoid duplicates in staging)
        db = MySQLdb.connect(host="etabib_db_updates", user="root", passwd="root", db="drug_updates", charset='utf8mb4')
        cursor = db.cursor()
        cursor.execute("SELECT nom_fr FROM nom_commercial_staging")
        staged_brands = {row[0].strip().upper() for row in cursor.fetchall()}
        
        xl = pd.ExcelFile(file_path)
        
        # Define sheets and their statuses
        sheets_config = [
            {'name': 'Non Renouvelés ', 'status': 'NR'}, # Note the space if present in check output
            {'name': 'Retraits', 'status': 'R'}
        ]
        
        # Helper to find sheet name case-insensitively
        def find_sheet(partial_name):
            return next((s for s in xl.sheet_names if partial_name.strip().lower() in s.strip().lower()), None)

        for config in sheets_config:
            sheet_name = find_sheet(config['name'])
            if not sheet_name:
                self.stdout.write(self.style.WARNING(f"Sheet matching '{config['name']}' not found."))
                continue
                
            self.stdout.write(f"Processing sheet: {sheet_name} (Status: {config['status']})")
            df = xl.parse(sheet_name)
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            if 'NOM DE MARQUE' not in df.columns:
                continue

            # Identify New Brands
            excel_brands = df['NOM DE MARQUE'].dropna().astype(str).str.strip().unique()
            new_brands_in_sheet = []
            for brand in excel_brands:
                norm_brand = brand.upper()
                if norm_brand not in existing_brands_norm and norm_brand not in staged_brands:
                    new_brands_in_sheet.append(brand)
            
            self.stdout.write(f"  Found {len(new_brands_in_sheet)} new brands to import.")
            
            if not new_brands_in_sheet:
                continue

            # Filter DF
            df['BRAND_NORM'] = df['NOM DE MARQUE'].astype(str).str.strip().str.upper()
            new_brands_set = set(b.upper() for b in new_brands_in_sheet)
            df_filtered = df[df['BRAND_NORM'].isin(new_brands_set)].copy()
            
            # Insert into nom_commercial_staging
            insert_brand_sql = "INSERT INTO nom_commercial_staging (unique_id, nom_fr) VALUES (%s, %s)"
            brand_values = []
            brand_map = {} # brand_name -> unique_id
            
            for brand in new_brands_in_sheet:
                # Clean brand name: remove excessive whitespace
                clean_brand = " ".join(brand.split())
                if len(clean_brand) > 255:
                    self.stdout.write(self.style.WARNING(f"Truncating brand '{clean_brand}' to 255 chars."))
                    clean_brand = clean_brand[:255]
                
                uid = f"nc_{uuid.uuid4().hex}"
                brand_values.append((uid, clean_brand))
                brand_map[brand.upper()] = uid # Map original upper to uid
                staged_brands.add(brand.upper()) # Add original to cache
            
            cursor.executemany(insert_brand_sql, brand_values)
            self.stdout.write(f"  Inserted {len(brand_values)} brands into nom_commercial_staging.")

            # Insert into medicament_staging
            # We need to map columns similar to transform_nomenclature.py
            # But we can simplify since we know the structure
            
            # Column Mapping (simplified from transform_nomenclature)
            col_map = {
                'dci_pays': 'DENOMINATION COMMUNE',
                'dosage': 'DOSAGE',
                'forme': 'FORME',
                'cond': 'CONDITIONNEMENT',
                'laboratoire': 'LABORATOIRE',
                'pays_labo': 'PAYS',
                'num_enregistrement': 'N° ENREGISTREMENT',
                'type': 'TYPE',
                'liste': 'LISTE',
                'duree_stabilitee': 'DUREE DE STABILITE',
                'remboursable': 'REMBOURSABLE',
                'nom_commercial': 'NOM DE MARQUE'
            }
            
            # Find actual columns in DF
            actual_col_map = {}
            for k, v in col_map.items():
                # Find column that contains v
                match = next((c for c in df.columns if v in c), None)
                if match:
                    actual_col_map[k] = match
            
            insert_med_sql = """
                INSERT INTO medicament_staging (
                    unique_id, dci_pays, nom_commercial_id, num_enregistrement, code, forme, dosage, cond, liste, 
                    laboratoire, type, duree_stabilitee, remboursable, pays_labo, amm_status, deleted
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
            """
            
            # Handle NaN values
            df_filtered = df_filtered.where(pd.notnull(df_filtered), None)

            med_values = []
            for _, row in df_filtered.iterrows():
                uid = f"med_{uuid.uuid4().hex}"
                brand_name = str(row.get(actual_col_map.get('nom_commercial'))).strip()
                brand_id = brand_map.get(brand_name.upper())
                
                def get_val(col_key, limit=255):
                    val = row.get(actual_col_map.get(col_key))
                    if val and isinstance(val, str) and len(val) > limit:
                        return val[:limit]
                    return val

                med_values.append((
                    uid,
                    get_val('dci_pays'),
                    brand_id,
                    get_val('num_enregistrement', 25), # num_enregistrement is varchar(25)
                    None, # code
                    get_val('forme'),
                    get_val('dosage'),
                    get_val('cond'),
                    get_val('liste', 64), # liste is varchar(64)
                    get_val('laboratoire'),
                    get_val('type', 30), # type is varchar(30)
                    get_val('duree_stabilitee'),
                    get_val('remboursable', 5), # remboursable is varchar(5)
                    get_val('pays_labo'),
                    config['status'] # amm_status
                ))
            
            cursor.executemany(insert_med_sql, med_values)
            self.stdout.write(f"  Inserted {len(med_values)} medicaments into medicament_staging.")

        db.commit()
        cursor.close()
        db.close()
        self.stdout.write(self.style.SUCCESS("Import of missing drugs complete."))
