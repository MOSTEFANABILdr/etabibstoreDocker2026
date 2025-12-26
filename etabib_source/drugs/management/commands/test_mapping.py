from django.core.management.base import BaseCommand
from drugs.models import DciAtc
import MySQLdb
import re

class Command(BaseCommand):
    help = 'Test semantic DCI mapping logic'

    def handle(self, *args, **options):
        # 1. Fetch Existing DCIs (The "ATC Nouns")
        self.stdout.write("Fetching existing DCIs...")
        existing_dcis = list(DciAtc.objects.filter(deleted=False).values('id', 'designation_fr', 'designation_ar'))
        self.stdout.write(f"Loaded {len(existing_dcis)} existing DCIs.")

        # 2. Fetch "New DCIs" from Update DB
        try:
            db = MySQLdb.connect(host="etabib_db_updates", user="root", passwd="root", db="drug_updates", charset='utf8mb4')
            cursor = db.cursor()
            cursor.execute("SELECT id, designation FROM new_dcis")
            new_dcis = cursor.fetchall()
            cursor.close()
            db.close()
            self.stdout.write(f"Loaded {len(new_dcis)} new DCIs to test.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to connect to update DB: {e}"))
            return

        # 3. Match
        matches = []
        ambiguous = []
        no_match = []

        # 3. Match Logic (Token Set Approach)
        # Stop words to ignore
        STOP_WORDS = {'ET', 'DE', 'LE', 'LA', 'EN', 'OU', 'AND', '+', '/', ',', '(', ')', '-'}

        def tokenize(text):
            # Replace separators with spaces
            text = text.replace('/', ' ').replace('+', ' ').replace(',', ' ').replace('-', ' ').replace('(', ' ').replace(')', ' ')
            # Split and clean
            tokens = set()
            for t in text.split():
                t_clean = t.strip().upper()
                if t_clean and t_clean not in STOP_WORDS:
                    tokens.add(t_clean)
            return tokens

        # Pre-process existing DCIs
        processed_existing = []
        for ex in existing_dcis:
            name = ex['designation_fr'] or ""
            tokens = tokenize(name)
            if tokens:
                processed_existing.append({
                    'id': ex['id'],
                    'name': name,
                    'tokens': tokens,
                    'token_count': len(tokens)
                })
        
        # Sort by token count desc (to prefer "A + B" over "A")
        processed_existing.sort(key=lambda x: x['token_count'], reverse=True)

        for new_id, new_dci_name in new_dcis:
            if not new_dci_name:
                continue
                
            new_tokens = tokenize(new_dci_name)
            if not new_tokens:
                no_match.append(new_dci_name)
                continue

            candidates = []
            
            for ex in processed_existing:
                # Check if existing DCI tokens are a SUBSET of new DCI tokens
                # e.g. {VALSARTAN, AMLODIPINE} <= {VALSARTAN, AMLODIPINE, HYDROCHLOROTHIAZIDE} -> True
                # e.g. {VALSARTAN} <= {VALSARTAN, AMLODIPINE} -> True
                if ex['tokens'].issubset(new_tokens):
                    candidates.append(ex)
            
            # Select Best Match
            # Candidates are already sorted by length desc.
            # The first one is the longest subset (most specific).
            # But we might have ties? e.g. "A B" and "B A" (same length).
            
            if not candidates:
                no_match.append(new_dci_name)
            else:
                best_candidate = candidates[0]
                
                # Check for ties in token count (Ambiguity)
                # e.g. if we have "AMOX + CLAV" and "CLAV + AMOX" as separate entries (unlikely but possible)
                ties = [c for c in candidates if c['token_count'] == best_candidate['token_count']]
                
                if len(ties) == 1:
                    matches.append({
                        'new': new_dci_name,
                        'matched': best_candidate['name'],
                        'id': best_candidate['id']
                    })
                else:
                    # Ambiguous tie
                    ambiguous.append({
                        'new': new_dci_name,
                        'matches': [c['name'] for c in ties]
                    })

        # 4. Save to DB for User Inspection
        self.stdout.write("Saving results to 'dci_mapping_preview' table...")
        try:
            db = MySQLdb.connect(host="etabib_db_updates", user="root", passwd="root", db="drug_updates", charset='utf8mb4')
            cursor = db.cursor()
            
            cursor.execute("DROP TABLE IF EXISTS dci_mapping_preview")
            cursor.execute("""
                CREATE TABLE dci_mapping_preview (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    new_dci VARCHAR(500),
                    match_status VARCHAR(50), -- MATCHED, AMBIGUOUS, NEW
                    matched_dci VARCHAR(500),
                    matched_id INT,
                    notes TEXT
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)
            
            # Insert Matches
            for m in matches:
                cursor.execute("""
                    INSERT INTO dci_mapping_preview (new_dci, match_status, matched_dci, matched_id)
                    VALUES (%s, 'MATCHED', %s, %s)
                """, [m['new'], m['matched'], m['id']])
                
            # Insert Ambiguous
            for m in ambiguous:
                cursor.execute("""
                    INSERT INTO dci_mapping_preview (new_dci, match_status, notes)
                    VALUES (%s, 'AMBIGUOUS', %s)
                """, [m['new'], str(m['matches'])])
                
            # Insert No Match
            for nm in no_match:
                cursor.execute("""
                    INSERT INTO dci_mapping_preview (new_dci, match_status)
                    VALUES (%s, 'NEW')
                """, [nm])
                
            db.commit()
            cursor.close()
            db.close()
            self.stdout.write(self.style.SUCCESS("Results saved to 'dci_mapping_preview' table."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to save to DB: {e}"))

        # 5. Report Summary (stdout)
        self.stdout.write("\n--- MATCHING RESULTS ---")
        self.stdout.write(f"Total Processed: {len(new_dcis)}")
        self.stdout.write(f"Matches Found: {len(matches)}")
        self.stdout.write(f"Ambiguous: {len(ambiguous)}")
        self.stdout.write(f"No Match (Truly New): {len(no_match)}")
