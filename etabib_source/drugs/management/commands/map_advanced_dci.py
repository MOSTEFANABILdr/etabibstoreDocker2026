from django.core.management.base import BaseCommand
from drugs.models import DciAtc
import MySQLdb
import uuid
import re
from difflib import SequenceMatcher

class Command(BaseCommand):
    help = 'Advanced DCI mapping with cleaning, fuzzy matching, and new DCI creation'

    def handle(self, *args, **options):
        # --- CONFIGURATION ---
        SALTS = [
            'SULFATE', 'CHLORHYDRATE', 'CILEXETIL', 'SODIQUE', 'POTASSIQUE', 'CALCIQUE', 
            'DIHYDRATE', 'MALEATE', 'FUMARATE', 'MESILATE', 'TARTRATE', 'BENZOATE', 
            'ACETATE', 'VALERATE', 'PROPIONATE', 'ESTOLATE', 'SUCCINATE', 'PHOSPHATE', 
            'GLUCONATE', 'LACTATE', 'CITRATE', 'BROMHYDRATE', 'HEMIHYDRATE', 'ANHYDRE'
        ]
        STOP_WORDS = {'ET', 'DE', 'LE', 'LA', 'EN', 'OU', 'AND', '+', '/', ',', '(', ')', '-'}

        def clean_dci(text):
            if not text: return ""
            text = text.upper()
            
            # Rule 1b: EXPRIME EN
            if "EXPRIME EN" in text:
                parts = text.split("EXPRIME EN")
                if len(parts) > 1:
                    text = parts[1] # Take part after
            
            # Rule 4: Remove Salts
            for salt in SALTS:
                # Remove salt if it's a distinct word
                text = re.sub(r'\b' + re.escape(salt) + r'\b', '', text)
            
            # Cleanup spaces
            text = re.sub(r'\s+', ' ', text).strip()
            return text

        def tokenize(text):
            text = str(text).replace('/', ' ').replace('+', ' ').replace(',', ' ').replace('-', ' ').replace('(', ' ').replace(')', ' ')
            tokens = set()
            for t in text.split():
                t_clean = t.strip().upper()
                if t_clean and t_clean not in STOP_WORDS:
                    tokens.add(t_clean)
            return tokens

        def is_combination(text):
            return '/' in text

        def count_components(text):
            return text.count('/') + 1

        # --- 1. Fetch Existing DCIs ---
        self.stdout.write("Fetching existing DCIs...")
        existing_dcis = list(DciAtc.objects.filter(deleted=False).values('unique_id', 'designation_fr'))
        
        # Pre-process existing DCIs
        processed_existing = []
        for ex in existing_dcis:
            name = ex['designation_fr'] or ""
            cleaned_name = clean_dci(name)
            tokens = tokenize(cleaned_name)
            if tokens:
                processed_existing.append({
                    'unique_id': ex['unique_id'],
                    'name': name,
                    'cleaned_name': cleaned_name,
                    'tokens': tokens,
                    'token_count': len(tokens),
                    'is_combo': is_combination(name),
                    'comp_count': count_components(name)
                })
        
        self.stdout.write(f"Loaded {len(processed_existing)} existing DCIs.")

        # --- 2. Connect to Staging DB ---
        self.stdout.write("Connecting to drug_updates DB...")
        try:
            db = MySQLdb.connect(host="etabib_db_updates", user="root", passwd="root", db="drug_updates", charset='utf8mb4')
            cursor = db.cursor(MySQLdb.cursors.DictCursor)

            # Add mapping_status column if not exists
            try:
                cursor.execute("ALTER TABLE medicament_staging ADD COLUMN mapping_status VARCHAR(50)")
            except:
                pass # Already exists

            # Create new_dci_atc table
            cursor.execute("DROP TABLE IF EXISTS new_dci_atc")
            cursor.execute("""
                CREATE TABLE new_dci_atc (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    unique_id VARCHAR(255) UNIQUE,
                    designation_fr VARCHAR(255),
                    original_dci VARCHAR(500)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)

            # Fetch unmapped rows
            cursor.execute("SELECT id, dci_pays FROM medicament_staging WHERE dci_atc_id IS NULL OR dci_atc_id = ''")
            rows = cursor.fetchall()
            self.stdout.write(f"Found {len(rows)} unmapped rows.")

            updates = []
            new_dcis_to_insert = []
            new_dci_map = {} # map cleaned_dci -> unique_id to reuse IDs for same new DCI

            for row in rows:
                original_dci = row['dci_pays']
                if not original_dci:
                    continue
                
                cleaned_dci = clean_dci(original_dci)
                row_tokens = tokenize(cleaned_dci)
                row_is_combo = is_combination(original_dci)
                row_comp_count = count_components(original_dci)
                
                match_found = None
                match_type = None
                
                # --- MATCHING LOGIC ---
                
                # Filter candidates by combination structure (Rule 2)
                # If row is combo, candidate must be combo with same count (approx)
                # Or if row is NOT combo, candidate should NOT be combo?
                # Let's be lenient: if row has '/', look for candidates with similar token count
                
                candidates = processed_existing
                
                # Strategy A: Token Set Match (Exact Subset/Superset)
                # We want the existing DCI to be the "core" of the new DCI
                # e.g. New: "AMOXICILLINE TRIHYDRATE" (Cleaned: "AMOXICILLINE") -> Existing: "AMOXICILLINE"
                
                best_match = None
                best_score = 0
                
                for ex in candidates:
                    # Semantic Check: Token Overlap
                    # Jaccard Similarity for tokens
                    intersection = len(row_tokens.intersection(ex['tokens']))
                    union = len(row_tokens.union(ex['tokens']))
                    
                    if union == 0: continue
                    
                    jaccard = intersection / union
                    
                    # Fuzzy String Check (Levenstein) on cleaned names
                    # Only if Jaccard is decent or if names are very similar
                    ratio = SequenceMatcher(None, cleaned_dci, ex['cleaned_name']).ratio()
                    
                    # Combined Score
                    score = (jaccard * 0.6) + (ratio * 0.4)
                    
                    if score > best_score:
                        best_score = score
                        best_match = ex
                
                # Thresholds
                if best_score > 0.85:
                    match_found = best_match
                    match_type = 'MATCHED_ADVANCED'
                elif best_score > 0.6:
                    match_found = best_match
                    match_type = 'AMBIGUOUS' # Needs verification
                
                # --- ACTION ---
                
                if match_found and match_type == 'MATCHED_ADVANCED':
                    updates.append({
                        'id': row['id'],
                        'dci_atc_id': match_found['unique_id'],
                        'status': match_type
                    })
                elif match_found and match_type == 'AMBIGUOUS':
                     updates.append({
                        'id': row['id'],
                        'dci_atc_id': match_found['unique_id'], # Propose it but flag
                        'status': 'TO_VERIFY'
                    })
                else:
                    # NO MATCH -> Create New DCI
                    # Check if we already created a new DCI for this cleaned name
                    if cleaned_dci in new_dci_map:
                        new_uid = new_dci_map[cleaned_dci]
                    else:
                        new_uid = f"dci_{uuid.uuid4().hex}"
                        new_dci_map[cleaned_dci] = new_uid
                        new_dcis_to_insert.append((new_uid, cleaned_dci, original_dci))
                    
                    updates.append({
                        'id': row['id'],
                        'dci_atc_id': new_uid,
                        'status': 'NEW_DCI'
                    })

            # --- EXECUTE UPDATES ---
            
            # 1. Insert New DCIs
            if new_dcis_to_insert:
                self.stdout.write(f"Creating {len(new_dcis_to_insert)} new DCI records...")
                insert_dci_sql = "INSERT INTO new_dci_atc (unique_id, designation_fr, original_dci) VALUES (%s, %s, %s)"
                
                batch_size = 1000
                for i in range(0, len(new_dcis_to_insert), batch_size):
                    batch = new_dcis_to_insert[i:i+batch_size]
                    cursor.executemany(insert_dci_sql, batch)
            
            # 2. Update Medicament Staging
            if updates:
                self.stdout.write(f"Updating {len(updates)} medicament records...")
                update_sql = "UPDATE medicament_staging SET dci_atc_id = %s, mapping_status = %s WHERE id = %s"
                
                batch_values = [(u['dci_atc_id'], u['status'], u['id']) for u in updates]
                
                for i in range(0, len(batch_values), batch_size):
                    batch = batch_values[i:i+batch_size]
                    cursor.executemany(update_sql, batch)
                    self.stdout.write(f"Updated {min(i+batch_size, len(batch_values))}/{len(batch_values)}...")

            db.commit()
            cursor.close()
            db.close()
            self.stdout.write(self.style.SUCCESS("Advanced mapping complete."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
