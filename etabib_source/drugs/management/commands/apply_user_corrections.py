from django.core.management.base import BaseCommand
import MySQLdb

class Command(BaseCommand):
    help = 'Apply user corrections from new_dci_atc and finalize staging'

    def handle(self, *args, **options):
        self.stdout.write("Connecting to drug_updates DB...")
        try:
            db = MySQLdb.connect(host="etabib_db_updates", user="root", passwd="root", db="drug_updates", charset='utf8mb4')
            cursor = db.cursor()

            # 1. Apply Corrections to Medicament Staging
            self.stdout.write("Applying corrections to medicament_staging...")
            
            # Update medicament_staging where new_dci_atc has a correct_dci_atc_id
            # We join on the current dci_atc_id (which points to the temporary unique_id in new_dci_atc)
            
            update_sql = """
                UPDATE medicament_staging ms
                JOIN new_dci_atc nda ON ms.dci_atc_id = nda.unique_id
                SET ms.dci_atc_id = nda.correct_dci_atc_id,
                    ms.mapping_status = 'USER_CORRECTED'
                WHERE nda.correct_dci_atc_id IS NOT NULL AND nda.correct_dci_atc_id != ''
            """
            cursor.execute(update_sql)
            corrected_count = cursor.rowcount
            self.stdout.write(f"Updated {corrected_count} rows in medicament_staging with user corrections.")

            # 2. Prune new_dci_atc Table
            self.stdout.write("Pruning new_dci_atc table...")
            
            # Delete rows that were corrected (i.e., not truly new)
            delete_sql = "DELETE FROM new_dci_atc WHERE correct_dci_atc_id IS NOT NULL AND correct_dci_atc_id != ''"
            cursor.execute(delete_sql)
            deleted_count = cursor.rowcount
            self.stdout.write(f"Removed {deleted_count} corrected rows from new_dci_atc.")
            
            # 3. Verify Remaining New DCIs
            cursor.execute("SELECT COUNT(*) FROM new_dci_atc")
            remaining_count = cursor.fetchone()[0]
            self.stdout.write(f"Remaining truly new DCIs: {remaining_count}")

            db.commit()
            cursor.close()
            db.close()
            self.stdout.write(self.style.SUCCESS("User corrections applied and staging tables finalized."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
