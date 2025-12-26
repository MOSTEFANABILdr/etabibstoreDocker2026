from django.core.management.base import BaseCommand
from drugs.models import DciAtc, NomCommercial
import pandas as pd
import MySQLdb
import re

class Command(BaseCommand):
    help = 'Stage new brands and map their DCIs'

    def handle(self, *args, **options):
        file_path = '/app/drugs/updates_official/NOMENCLATURE-VERSION-NOVEMBRE-2025.xlsx'
        
        # 1. Fetch Existing Data
        self.stdout.write("Fetching existing Brands and DCIs...")
        
        # Existing Brands (Set for fast lookup)
        existing_brands = set(NomCommercial.objects.filter(deleted=False).values_list('nom_fr', flat=True))
        # Normalize existing brands for comparison (upper, strip)
        existing_brands_norm = {b.strip().upper() for b in existing_brands if b}
        
        # Existing DCIs (List of dicts for matching)
        existing_dcis = list(DciAtc.objects.filter(deleted=False).values('id', 'unique_id', 'designation_fr'))
        
        # Pre-process DCIs for Token Matching
        STOP_WORDS = {'ET', 'DE', 'LE', 'LA', 'EN', 'OU', 'AND', '+', '/', ',', '(', ')', '-'}
        
        def tokenize(text):
            if not text: return set()
            text = str(text).replace('/', ' ').replace('+', ' ').replace(',', ' ').replace('-', ' ').replace('(', ' ').replace(')', ' ')
            tokens = set()
            for t in text.split():
                t_clean = t.strip().upper()
                if t_clean and t_clean not in STOP_WORDS:
                    tokens.add(t_clean)
            return tokens

        processed_existing_dcis = []
        for ex in existing_dcis:
            name = ex['designation_fr'] or ""
            tokens = tokenize(name)
            if tokens:
                processed_existing_dcis.append({
                    'id': ex['id'],
                    'unique_id': ex['unique_id'],
                    'name': name,
                    'tokens': tokens,
                    'token_count': len(tokens)
                })
        # Sort by token count desc
        processed_existing_dcis.sort(key=lambda x: x['token_count'], reverse=True)
        
        self.stdout.write(f"Loaded {len(existing_brands_norm)} existing brands and {len(processed_existing_dcis)} existing DCIs.")

        # 2. Parse Excel
        self.stdout.write("Parsing Excel file...")
        try:
            xl = pd.ExcelFile(file_path)
            # Find Nomenclature sheet
            sheet_name = next((s for s in xl.sheet_names if 'nomenclature' in s.lower()), None)
            if not sheet_name:
                self.stdout.write(self.style.ERROR("Nomenclature sheet not found!"))
                return
            
            df = xl.parse(sheet_name)
            df.columns = [str(c).strip().upper() for c in df.columns]
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading Excel: {e}"))
            return

        # 3. Identify New Brands & Map DCIs
        staged_data = []
        
        for index, row in df.iterrows():
            brand_name = str(row.get('NOM DE MARQUE', '')).strip()
            excel_dci = str(row.get('DENOMINATION COMMUNE INTERNATIONALE', '')).strip()
            
            if not brand_name or brand_name == 'nan':
                continue
                
            # Check if Brand is New
            if brand_name.upper() in existing_brands_norm:
                continue # Skip existing brands
            
            # It's a New Brand! Map the DCI.
            match_status = 'NEW'
            mapped_dci_unique_id = None
            mapped_dci_name = None
            
            new_tokens = tokenize(excel_dci)
            
            if new_tokens:
                candidates = []
                for ex in processed_existing_dcis:
                    if ex['tokens'].issubset(new_tokens):
                        candidates.append(ex)
                
                if candidates:
                    best_candidate = candidates[0]
                    ties = [c for c in candidates if c['token_count'] == best_candidate['token_count']]
                    
                    if len(ties) == 1:
                        match_status = 'MATCHED'
                        mapped_dci_unique_id = best_candidate['unique_id']
                        mapped_dci_name = best_candidate['name']
                    else:
                        match_status = 'AMBIGUOUS'
                        # For ambiguous, maybe store the first one or leave null?
                        # Let's store the candidates in a note or just leave mapped fields null
                        mapped_dci_name = f"AMBIGUOUS: {[c['name'] for c in ties]}"

            staged_data.append({
                'brand_name': brand_name,
                'excel_dci': excel_dci,
                'mapped_dci_unique_id': mapped_dci_unique_id,
                'mapped_dci_name': mapped_dci_name,
                'match_status': match_status
            })

        self.stdout.write(f"Found {len(staged_data)} new brands.")

        # 4. Save to Staging Table
        self.stdout.write("Saving to 'brand_dci_mapping_staging' table...")
        try:
            db = MySQLdb.connect(host="etabib_db_updates", user="root", passwd="root", db="drug_updates", charset='utf8mb4')
            cursor = db.cursor()
            
            cursor.execute("DROP TABLE IF EXISTS brand_dci_mapping_staging")
            cursor.execute("""
                CREATE TABLE brand_dci_mapping_staging (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    brand_name VARCHAR(500),
                    excel_dci VARCHAR(500),
                    mapped_dci_unique_id VARCHAR(255),
                    mapped_dci_name TEXT,
                    match_status VARCHAR(50)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)
            
            for item in staged_data:
                cursor.execute("""
                    INSERT INTO brand_dci_mapping_staging 
                    (brand_name, excel_dci, mapped_dci_unique_id, mapped_dci_name, match_status)
                    VALUES (%s, %s, %s, %s, %s)
                """, [
                    item['brand_name'], 
                    item['excel_dci'], 
                    item['mapped_dci_unique_id'], 
                    item['mapped_dci_name'], 
                    item['match_status']
                ])
                
            db.commit()
            cursor.close()
            db.close()
            self.stdout.write(self.style.SUCCESS("Staging complete."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to save to DB: {e}"))
