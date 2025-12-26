import logging
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from core.models import Contact

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Merge contacts from core_contact_source into core_contact (Optimized)'

    def handle(self, *args, **options):
        self.stdout.write("Starting optimized contact merge process...")
        
        # 1. Load existing contacts
        self.stdout.write("Loading existing contacts...")
        existing_contacts = list(Contact.objects.all())
        self.stdout.write(f"Loaded {len(existing_contacts)} existing contacts.")

        # 2. Build Indexes
        self.stdout.write("Building indexes...")
        index_place_id = {}
        index_email = {}
        index_phone = {}
        index_pageweb = {}
        index_social = {} # Key: (network, value) -> contact

        def add_to_index(contact):
            if contact.place_id:
                index_place_id[contact.place_id] = contact
            if contact.email:
                index_email[contact.email] = contact
            if contact.pageweb:
                index_pageweb[contact.pageweb] = contact
            
            for phone in [contact.mobile, contact.mobile_1, contact.mobile_2, contact.fixe]:
                if phone:
                    index_phone[phone] = contact
            
            if contact.facebook: index_social[('facebook', contact.facebook)] = contact
            if contact.linkedin: index_social[('linkedin', contact.linkedin)] = contact
            if contact.twitter: index_social[('twitter', contact.twitter)] = contact
            if contact.instagram: index_social[('instagram', contact.instagram)] = contact

        for c in existing_contacts:
            add_to_index(c)

        # 3. Process Source Data
        self.stdout.write("Fetching source data...")
        source_contacts = self.fetch_source_contacts()
        self.stdout.write(f"Processing {len(source_contacts)} source records...")

        new_contacts = []
        updated_contacts = set()
        
        # Fields to check/update
        fields_to_update = [
            'nom', 'prenom', 'date_naissance', 'sexe', 'adresse', 'fixe', 'mobile', 
            'email', 'commentaire', 'fonction', 'departement', 'commune', 'codepostal', 
            'pageweb', 'facebook', 'instagram', 'linkedin', 'twitter', 'gps', 
            'mobile_1', 'mobile_2', 'place_id', 'maps_url', 'organisme', 'type_exercice',
            'source', 'motif'
        ]

        for i, source_data in enumerate(source_contacts):
            if i % 5000 == 0:
                self.stdout.write(f"Processed {i} records...")

            match = None
            
            # Match Logic (Priority)
            if source_data.get('place_id') and source_data['place_id'] in index_place_id:
                match = index_place_id[source_data['place_id']]
            
            if not match:
                phones = [source_data.get(p) for p in ['mobile', 'mobile_1', 'mobile_2', 'fixe'] if source_data.get(p)]
                for phone in phones:
                    if phone in index_phone:
                        match = index_phone[phone]
                        break
            
            if not match and source_data.get('email') and source_data['email'] in index_email:
                match = index_email[source_data['email']]
            
            if not match:
                for net in ['facebook', 'linkedin', 'twitter', 'instagram']:
                    val = source_data.get(net)
                    if val and (net, val) in index_social:
                        match = index_social[(net, val)]
                        break
            
            if not match and source_data.get('pageweb') and source_data['pageweb'] in index_pageweb:
                match = index_pageweb[source_data['pageweb']]

            # Update or Create
            if match:
                updated = False
                for field in fields_to_update:
                    target_val = getattr(match, field)
                    source_val = source_data.get(field)
                    if not target_val and source_val:
                        setattr(match, field, source_val)
                        updated = True
                
                if updated:
                    if match.pk:
                        updated_contacts.add(match)
                    # If no pk, it's in new_contacts list, so it will be created with updated values.
                    
                    # Re-index if we updated fields used for indexing? 
                    # For simplicity, we assume we only fill EMPTY fields, so we don't overwrite existing index keys.
                    # But if we filled an empty phone, we should add it to index to match subsequent duplicates.
                    add_to_index(match)

            else:
                # Create new
                data = source_data.copy()
                if 'id' in data: del data['id']
                
                new_contact = Contact(**data)
                new_contacts.append(new_contact)
                add_to_index(new_contact) # Add to index to catch duplicates in source

        # 4. Save Changes
        self.stdout.write(f"Saving {len(new_contacts)} new contacts...")
        batch_size = 1000
        Contact.objects.bulk_create(new_contacts, batch_size=batch_size)
        
        self.stdout.write(f"Updating {len(updated_contacts)} existing contacts...")
        if updated_contacts:
            Contact.objects.bulk_update(list(updated_contacts), fields_to_update, batch_size=batch_size)

        self.stdout.write(self.style.SUCCESS("Merge complete!"))

    def fetch_source_contacts(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM core_contact_source")
            columns = [col[0] for col in cursor.description]
            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
