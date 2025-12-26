from django.core.management.base import BaseCommand
from drugs.models import Medicament, MapAutorise
import MySQLdb

class Command(BaseCommand):
    help = 'Fix AMM data for previously injected records'

    def handle(self, *args, **options):
        self.stdout.write("Connecting to drug_updates DB...")
        db = MySQLdb.connect(host="etabib_db_updates", user="root", passwd="root", db="drug_updates", charset='utf8mb4')
        cursor = db.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute("SELECT unique_id, amm_status FROM medicament_staging")
        staging_rows = cursor.fetchall()
        
        self.stdout.write(f"Checking {len(staging_rows)} staged medicaments...")
        
        updated_meds = 0
        created_maps = 0
        
        for row in staging_rows:
            uid = row['unique_id']
            status = row['amm_status'] or 'A' # Default to A if missing (shouldn't be)
            
            try:
                med = Medicament.objects.get(unique_id=uid)
                
                # 1. Update Medicament.autorise if needed
                if med.autorise != status:
                    med.autorise = status
                    med.save() # This triggers signals! which might create MapAutorise?
                    # Let's check if signal creates MapAutorise.
                    # signals.py: pre_save_mapautorise updates MapAutorise table.
                    # pre_save_medicament updates Medicament table.
                    # There is NO signal that creates MapAutorise when Medicament is saved.
                    updated_meds += 1
                
                # 2. Create/Update MapAutorise
                # Check if exists
                if not MapAutorise.objects.filter(medicament=med).exists():
                    MapAutorise.objects.create(medicament=med, autorise=status)
                    created_maps += 1
                else:
                    ma = MapAutorise.objects.get(medicament=med)
                    if ma.autorise != status:
                        ma.autorise = status
                        ma.save()
                        
            except Medicament.DoesNotExist:
                # Should not happen if injection worked
                pass
                
        self.stdout.write(f"Updated {updated_meds} Medicament records.")
        self.stdout.write(f"Created {created_maps} MapAutorise records.")
        
        cursor.close()
        db.close()
