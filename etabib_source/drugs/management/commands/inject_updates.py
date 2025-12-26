from django.core.management.base import BaseCommand
from django.db import transaction, connections
from drugs.models import Medicament, DciAtc, NomCommercial, MapAutorise
import MySQLdb

class Command(BaseCommand):
    help = 'Inject staged data into the main database'

    def handle(self, *args, **options):
        self.stdout.write("Connecting to drug_updates DB...")
        try:
            # Connect to Staging DB
            staging_db = MySQLdb.connect(host="etabib_db_updates", user="root", passwd="root", db="drug_updates", charset='utf8mb4')
            staging_cursor = staging_db.cursor(MySQLdb.cursors.DictCursor)

            # --- 1. Inject New DCIs ---
            self.stdout.write("Fetching new DCIs from staging...")
            staging_cursor.execute("SELECT * FROM new_dci_atc")
            new_dcis = staging_cursor.fetchall()
            
            self.stdout.write(f"Injecting {len(new_dcis)} new DCIs into Main DB...")
            
            with transaction.atomic():
                dci_objects = []
                for row in new_dcis:
                    # Check if exists (safety)
                    if not DciAtc.objects.filter(unique_id=row['unique_id']).exists():
                        dci_objects.append(DciAtc(
                            unique_id=row['unique_id'],
                            designation_fr=row['designation_fr'],
                            # Add other fields if necessary, e.g. deleted=False
                        ))
                
                if dci_objects:
                    DciAtc.objects.bulk_create(dci_objects)
                    self.stdout.write(f"Created {len(dci_objects)} DciAtc records.")
                else:
                    self.stdout.write("No new DciAtc records to create (or all existed).")

            # --- 2. Inject New Brands ---
            self.stdout.write("Fetching new Brands from staging...")
            staging_cursor.execute("SELECT * FROM nom_commercial_staging")
            new_brands = staging_cursor.fetchall()
            
            self.stdout.write(f"Injecting {len(new_brands)} new Brands into Main DB...")
            
            with transaction.atomic():
                brand_objects = []
                for row in new_brands:
                    if not NomCommercial.objects.filter(unique_id=row['unique_id']).exists():
                        brand_objects.append(NomCommercial(
                            unique_id=row['unique_id'],
                            nom_fr=row['nom_fr'],
                            deleted=False
                        ))
                
                if brand_objects:
                    NomCommercial.objects.bulk_create(brand_objects)
                    self.stdout.write(f"Created {len(brand_objects)} NomCommercial records.")
                else:
                    self.stdout.write("No new NomCommercial records to create.")

            # --- 3. Inject Medicaments ---
            self.stdout.write("Fetching Medicaments from staging...")
            staging_cursor.execute("SELECT * FROM medicament_staging")
            medicaments = staging_cursor.fetchall()
            
            self.stdout.write(f"Injecting {len(medicaments)} Medicaments into Main DB...")
            
            with transaction.atomic():
                med_objects = []
                map_autorise_objects = []
                
                for row in medicaments:
                    if not Medicament.objects.filter(unique_id=row['unique_id']).exists():
                        
                        med = Medicament(
                            unique_id=row['unique_id'],
                            pays_marche_id=row['pays_marche'], # Use _id to assign FK directly
                            dci_pays=row['dci_pays'],
                            dci_atc_id=row['dci_atc_id'], # FK to DciAtc.unique_id
                            nom_commercial_id=row['nom_commercial_id'], # FK to NomCommercial.unique_id
                            num_enregistrement=row['num_enregistrement'],
                            code=row['code'],
                            forme=row['forme'],
                            dosage=row['dosage'],
                            cond=row['cond'],
                            liste=row['liste'],
                            p1=row['p1'],
                            p2=row['p2'],
                            obs=row['obs'],
                            laboratoire=row['laboratoire'],
                            note_medecin=row['note_medecin'],
                            observation=row['observation'],
                            type=row['type'],
                            status=row['status'],
                            duree_stabilitee=row['duree_stabilitee'],
                            remboursable=row['remboursable'],
                            # forme_homogene_id=row['forme_homogene_id'], # Might be null
                            etat=row['etat'],
                            autorise=row['amm_status'], # Use amm_status from staging
                            date_retrait=row['date_retrait'],
                            motif_retrait=row['motif_retrait'],
                            # categorie_id=row['categorie_id'], # Might be null
                            pays_labo=row['pays_labo'],
                            # labo_id=row['labo_id'], # Might be null
                            deleted=False
                        )
                        med_objects.append(med)
                        
                        # Prepare MapAutorise object
                        # We need the Medicament instance or ID. Since we are bulk creating, we can't get the instance PK if it was an AutoField, 
                        # but here unique_id is the key used for relationships (to_field='unique_id').
                        # MapAutorise.medicament is OneToOneField to Medicament(to_field='unique_id').
                        # So we can just set medicament_id = unique_id.
                        
                        if row['amm_status']:
                             # MapAutorise has fields: medicament, autorise
                             # We use medicament_id to set the FK directly
                             map_autorise_objects.append(MapAutorise(
                                 medicament_id=row['unique_id'],
                                 autorise=row['amm_status']
                             ))

                if med_objects:
                    Medicament.objects.bulk_create(med_objects)
                    self.stdout.write(f"Created {len(med_objects)} Medicament records.")
                else:
                    self.stdout.write("No new Medicament records to create.")
                    
                if map_autorise_objects:
                    MapAutorise.objects.bulk_create(map_autorise_objects)
                    self.stdout.write(f"Created {len(map_autorise_objects)} MapAutorise records.")


            staging_cursor.close()
            staging_db.close()
            self.stdout.write(self.style.SUCCESS("Injection complete."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
