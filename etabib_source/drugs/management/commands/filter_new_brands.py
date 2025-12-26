from django.core.management.base import BaseCommand
from drugs.models import NomCommercial
import pandas as pd
import MySQLdb

class Command(BaseCommand):
    help = 'Filter nomenclature to include only new brands (all variations)'

    def handle(self, *args, **options):
        file_path = '/app/drugs/updates_official/NOMENCLATURE-VERSION-NOVEMBRE-2025.xlsx'
        
        # 1. Fetch Existing Brands
        self.stdout.write("Fetching existing Brands...")
        existing_brands = set(NomCommercial.objects.filter(deleted=False).values_list('nom_fr', flat=True))
        existing_brands_norm = {b.strip().upper() for b in existing_brands if b}
        self.stdout.write(f"Loaded {len(existing_brands_norm)} existing brands.")

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
            # Normalize columns
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            # Ensure 'NOM DE MARQUE' exists
            if 'NOM DE MARQUE' not in df.columns:
                self.stdout.write(self.style.ERROR("Column 'NOM DE MARQUE' not found in Excel!"))
                return

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading Excel: {e}"))
            return

        # 3. Identify New Brands
        # Get all unique brands from Excel
        excel_brands = df['NOM DE MARQUE'].dropna().astype(str).str.strip().unique()
        
        new_brands = []
        for brand in excel_brands:
            if brand.upper() not in existing_brands_norm:
                new_brands.append(brand)
        
        self.stdout.write(f"Identified {len(new_brands)} new brands in Excel.")
        
        # 4. Filter DataFrame
        # Keep rows where NOM DE MARQUE is in new_brands
        # We use the original case from Excel for filtering to be safe, or normalize?
        # Let's normalize the column for filtering
        df['BRAND_NORM'] = df['NOM DE MARQUE'].astype(str).str.strip().str.upper()
        new_brands_norm = set(b.upper() for b in new_brands)
        
        df_filtered = df[df['BRAND_NORM'].isin(new_brands_norm)].copy()
        df_filtered.drop(columns=['BRAND_NORM'], inplace=True)
        
        self.stdout.write(f"Filtered {len(df_filtered)} rows corresponding to new brands.")

        # 5. Save to DB
        self.stdout.write("Saving to 'filtered_nomenclature_new_brands' table...")
        try:
            db = MySQLdb.connect(host="etabib_db_updates", user="root", passwd="root", db="drug_updates", charset='utf8mb4')
            cursor = db.cursor()
            
            table_name = "filtered_nomenclature_new_brands"
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # Create Table dynamically based on columns
            # Map pandas types to MySQL types roughly
            create_cols = ["id INT AUTO_INCREMENT PRIMARY KEY"]
            cols = df_filtered.columns.tolist()
            
            for col in cols:
                # Use TEXT for everything to be safe and avoid length issues
                # Clean column name
                safe_col = col.replace(' ', '_').replace("'", "").replace("/", "_").replace(".", "")
                create_cols.append(f"`{safe_col}` TEXT")
            
            create_sql = f"CREATE TABLE {table_name} ({', '.join(create_cols)}) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            cursor.execute(create_sql)
            
            # Insert Data
            # Prepare INSERT statement
            safe_cols = []
            for c in cols:
                clean_c = c.replace(' ', '_').replace("'", "").replace("/", "_").replace(".", "")
                safe_cols.append(f"`{clean_c}`")
            
            placeholders = ["%s"] * len(cols)
            insert_sql = f"INSERT INTO {table_name} ({', '.join(safe_cols)}) VALUES ({', '.join(placeholders)})"
            
            # Convert DF to list of tuples, handling NaNs
            # Use object type to allow None replacement
            df_filtered = df_filtered.astype(object)
            data = df_filtered.where(pd.notnull(df_filtered), None).values.tolist()
            
            # Batch insert
            batch_size = 1000
            for i in range(0, len(data), batch_size):
                batch = data[i:i+batch_size]
                cursor.executemany(insert_sql, batch)
                self.stdout.write(f"Inserted {min(i+batch_size, len(data))}/{len(data)} rows...")
                
            db.commit()
            cursor.close()
            db.close()
            self.stdout.write(self.style.SUCCESS("Filtering and export complete."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to save to DB: {e}"))
