from django.core.management.base import BaseCommand
from core.models import Contact, Specialite
from django.db.models import Q

class Command(BaseCommand):
    help = 'Update specialty of doctors based on text matching'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the update without saving changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        self.stdout.write(f"Starting specialty update (Dry run: {dry_run})...")

        # Load all specialties
        specialties = Specialite.objects.all()
        # Create a lookup dict for objects to avoid DB hits in loop
        specialty_obj_map = {s.id: s for s in specialties}
        
        # Create a list of (id, keywords) tuples
        specialty_map = []
        for s in specialties:
            keywords = [s.libelle.lower()]
            if s.libelle_ar:
                keywords.append(s.libelle_ar.lower())
            specialty_map.append({'id': s.id, 'name': s.libelle, 'keywords': keywords})

        # MANUAL MAPPINGS (ID -> Extra Keywords)
        # 81: PHARMACIEN
        # 155: CLINIQUE
        # 172: HOPITAL
        extra_keywords = {
            81: ['pharmacie', 'pharmacy', 'pharm'],
            155: ['clinique', 'clinic'],
            172: ['hopital', 'hospital', 'chu', 'eph'],
            168: ['médecin', 'medecin'] # If user wants generic 'MEDECIN' mapped here
        }
        
        for item in specialty_map:
            if item['id'] in extra_keywords:
                item['keywords'].extend(extra_keywords[item['id']])

        # Fallback ID for "General Medicine" (ID 1 based on previous inspection)
        GENERAL_MEDICINE_ID = 1
        general_medicine_obj = specialty_obj_map.get(GENERAL_MEDICINE_ID)
        
        if not general_medicine_obj:
             self.stdout.write(f"Warning: General Medicine ID {GENERAL_MEDICINE_ID} not found in DB.")

        # Keywords that indicate the contact is a doctor
        DOCTOR_INDICATORS = [
            'dr', 'docteur', 'medecin', 'médecin', 'tabib', 'طبيب', 'دكتور', 'دكتورة', 'cabinet', 'عيادة'
        ]

        # Use iterator to avoid loading all objects into memory
        contacts = Contact.objects.all().iterator()
        # We can't count() an iterator easily without a separate query, so just print progress periodically
        total_contacts = Contact.objects.count()
        self.stdout.write(f"Processing {total_contacts} contacts...")
        
        updated_count = 0
        processed_count = 0
        
        for contact in contacts:
            processed_count += 1
            if processed_count % 1000 == 0:
                self.stdout.write(f"Processed {processed_count}/{total_contacts}...")

            # Skip if specialty is already set, as per user request to "insert the id" (implies filling gaps)
            if contact.specialite:
                continue
            
            original_specialite = contact.specialite
            new_specialite = None
            reason = ""

            # Normalize text for checking
            nom = (contact.nom or "").lower()
            prenom = (contact.prenom or "").lower()
            fonction = (contact.fonction or "").lower()
            adresse = (contact.adresse or "").lower()
            
            full_text = f"{nom} {prenom} {fonction} {adresse}"

            # 1. Search for specific specialty match
            matched_specialty = None
            for s_data in specialty_map:
                for keyword in s_data['keywords']:
                    if keyword in full_text:
                        matched_specialty = s_data
                        break
                if matched_specialty:
                    break
            
            if matched_specialty:
                # Use pre-fetched object
                new_specialite = specialty_obj_map.get(matched_specialty['id'])
                reason = f"Matched keyword: {matched_specialty['name']}"
            
            # 2. Fallback: If no specialty matched, but looks like a doctor
            elif any(ind in full_text for ind in DOCTOR_INDICATORS):
                # EXCLUDE PHARMACISTS from this fallback
                if 'pharmaci' in full_text or 'pharmacy' in full_text:
                     pass
                else:
                    # Assign General Medicine using pre-fetched object
                    if general_medicine_obj:
                        new_specialite = general_medicine_obj
                        reason = "Fallback: Doctor indicator found, assigned General Medicine"

            # 3. Apply Update
            if new_specialite and new_specialite != original_specialite:
                if dry_run:
                    self.stdout.write(f"[DRY RUN] ID {contact.id}: {contact.nom} {contact.prenom} | Current: {original_specialite} -> New: {new_specialite} [{reason}]")
                else:
                    contact.specialite = new_specialite
                    contact.save()
                    # Reduce verbosity for actual run, maybe only print every 100 updates?
                    # self.stdout.write(f"[UPDATED] ID {contact.id}: {contact.nom} {contact.prenom} -> {new_specialite} [{reason}]")
                updated_count += 1

        self.stdout.write(f"Done. Updates proposed/made: {updated_count}")
