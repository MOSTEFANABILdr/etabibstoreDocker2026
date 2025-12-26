import pandas as pd
from django.core.management.base import BaseCommand
from drugs.models import NomCommercial

class Command(BaseCommand):
    help = 'Check other sheets for new brands'

    def handle(self, *args, **options):
        file_path = '/app/drugs/updates_official/NOMENCLATURE-VERSION-NOVEMBRE-2025.xlsx'
        
        # 1. Fetch Existing Brands (DB + Staging)
        existing_brands = set(NomCommercial.objects.filter(deleted=False).values_list('nom_fr', flat=True))
        existing_brands_norm = {b.strip().upper() for b in existing_brands if b}
        
        # Add brands we already staged
        # (Assuming we don't want to re-import what we already have, but we want to know if we missed any)
        # Actually, let's just see if there are brands in these sheets that are NOT in the Main DB.
        
        xl = pd.ExcelFile(file_path)
        print(f"Sheets found: {xl.sheet_names}")
        
        sheets_to_check = [s for s in xl.sheet_names if 'nomenclature' not in s.lower()]
        
        for sheet in sheets_to_check:
            print(f"\nChecking sheet: {sheet}")
            try:
                df = xl.parse(sheet)
                df.columns = [str(c).strip().upper() for c in df.columns]
                
                if 'NOM DE MARQUE' not in df.columns:
                    print(f"  Skipping (No 'NOM DE MARQUE' column)")
                    continue
                
                sheet_brands = df['NOM DE MARQUE'].dropna().astype(str).str.strip().unique()
                
                new_in_sheet = []
                for brand in sheet_brands:
                    if brand.upper() not in existing_brands_norm:
                        new_in_sheet.append(brand)
                
                print(f"  Found {len(new_in_sheet)} brands NOT in Main DB.")
                if new_in_sheet:
                    print(f"  Examples: {new_in_sheet[:5]}")
                    
            except Exception as e:
                print(f"  Error reading sheet: {e}")
