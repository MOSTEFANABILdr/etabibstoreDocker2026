from django.core.management.base import BaseCommand
from drugs.models import Medicament, DciAtc, NomCommercial, FormeHomogene, MedicCategorie, Laboratoire
import pandas as pd
import json
import os

class Command(BaseCommand):
    help = 'Analyze drug updates from Excel file'

    def handle(self, *args, **options):
        file_path = '/app/drugs/updates_official/NOMENCLATURE-VERSION-NOVEMBRE-2025.xlsx'
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        self.stdout.write(f"Analyzing {file_path}...")
        
        report = {
            'stats': {
                'total_rows': 0,
                'found_by_reg': 0,
                'found_by_composite': 0,
                'not_found_new': 0,
                'status_updates': 0,
                'retrait_updates': 0,
            },
            'new_dcis': set(),
            'new_brands': set(),
            'updates': [],
            'new_drugs': []
        }

        try:
            xl = pd.ExcelFile(file_path)
            
            # 1. Process Nomenclature (Main List)
            if 'Nomenclature' in xl.sheet_names:
                df = xl.parse('Nomenclature')
                self.process_sheet(df, report, is_retrait=False)
            
            # 2. Process Retraits
            if 'Retraits' in xl.sheet_names:
                df_retrait = xl.parse('Retraits')
                self.process_sheet(df_retrait, report, is_retrait=True)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
            return

        # Convert sets to lists for JSON serialization
        report['new_dcis'] = list(report['new_dcis'])
        report['new_brands'] = list(report['new_brands'])
        
        # Print report to stdout
        self.stdout.write("JSON_REPORT_START")
        self.stdout.write(json.dumps(report, indent=4, ensure_ascii=False))
        self.stdout.write("JSON_REPORT_END")
            
        self.stdout.write(self.style.SUCCESS(f"Analysis complete."))
        self.stdout.write(f"Stats: {report['stats']}")

    def process_sheet(self, df, report, is_retrait):
        # Normalize columns
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        for index, row in df.iterrows():
            report['stats']['total_rows'] += 1
            
            # Extract fields
            reg_num = str(row.get('N°ENREGISTREMENT', '')).strip()
            dci_name = str(row.get('DENOMINATION COMMUNE INTERNATIONALE', '')).strip()
            brand_name = str(row.get('NOM DE MARQUE', '')).strip()
            forme = str(row.get('FORME', '')).strip()
            dosage = str(row.get('DOSAGE', '')).strip()
            cond = str(row.get('CONDITIONNEMENT', '')).strip()
            
            # Try to find existing medicament
            medicament = None
            
            # 1. By Registration Number
            if reg_num and reg_num != 'nan':
                medicament = Medicament.objects.filter(num_enregistrement=reg_num).first()
                if medicament:
                    report['stats']['found_by_reg'] += 1
            
            # 2. By Composite Key (if not found)
            if not medicament:
                # Try to match by DCI + Brand + Form + Dosage (fuzzy match might be needed, but exact for now)
                # We need to find IDs for DCI and Brand first to query
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
                        report['stats']['found_by_composite'] += 1

            # Analyze Changes
            if medicament:
                changes = {}
                
                if is_retrait:
                    date_retrait = str(row.get('DATE DE RETRAIT', '')).strip()
                    motif_retrait = str(row.get('MOTIF DE RETRAIT', '')).strip()
                    
                    if medicament.date_retrait != date_retrait:
                        changes['date_retrait'] = {'old': medicament.date_retrait, 'new': date_retrait}
                    if medicament.motif_retrait != motif_retrait:
                        changes['motif_retrait'] = {'old': medicament.motif_retrait, 'new': motif_retrait}
                        
                    if changes:
                        report['stats']['retrait_updates'] += 1
                        report['updates'].append({
                            'id': medicament.id,
                            'reg_num': reg_num,
                            'type': 'retrait',
                            'changes': changes
                        })
                else:
                    # Check Status / Remboursable
                    # Map Excel columns to DB fields
                    # STATUT -> status?
                    # REMBOURSABLE -> remboursable?
                    
                    new_status = str(row.get('STATUT', '')).strip()
                    # new_remb = str(row.get('REMBOURSABLE', '')).strip() # Column name might vary, check inspection
                    
                    if new_status and new_status != 'nan' and medicament.status != new_status:
                        changes['status'] = {'old': medicament.status, 'new': new_status}
                        
                    if changes:
                        report['stats']['status_updates'] += 1
                        report['updates'].append({
                            'id': medicament.id,
                            'reg_num': reg_num,
                            'type': 'update',
                            'changes': changes
                        })
            else:
                # New Drug
                report['stats']['not_found_new'] += 1
                report['new_drugs'].append({
                    'reg_num': reg_num,
                    'dci': dci_name,
                    'brand': brand_name,
                    'forme': forme,
                    'dosage': dosage,
                    'cond': cond,
                    'laboratoire': str(row.get("LABORATOIRES DETENTEUR DE LA DECISION D'ENREGISTREMENT", '')).strip(),
                    'pays': str(row.get("PAYS DU LABORATOIRE DETENTEUR DE LA DECISION D'ENREGISTREMENT", '')).strip()
                })
                
                # Check if DCI/Brand are new
                if not DciAtc.objects.filter(designation_fr__iexact=dci_name).exists():
                    report['new_dcis'].add(dci_name)
                if not NomCommercial.objects.filter(nom_fr__iexact=brand_name).exists():
                    report['new_brands'].add(brand_name)
