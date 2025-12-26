from django.core.management.base import BaseCommand
from core.models import Contact
import re

class Command(BaseCommand):
    help = 'Update gender (sexe) of doctors based on title and name'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the update without saving changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        self.stdout.write(f"Starting gender update (Dry run: {dry_run})...")

        # Regex patterns for titles
        # \b matches word boundary, but for Arabic we might need to be careful.
        # Simple containment check is often safer for dirty data.
        FEMALE_TITLES = [r'دكتورة', r'Dr\.? ?Mrs', r'Mme']
        MALE_TITLES = [r'دكتور', r'Dr\.? ?Mr', r'Mr']

        # Common names dictionary (extensible)
        FEMALE_NAMES = {
            'fatima', 'zohra', 'khadidja', 'aicha', 'meriem', 'sarah', 'amina', 'karima', 
            'nassima', 'samira', 'latifa', 'houria', 'souad', 'fatiha', 'yamina', 'rachida',
            'naima', 'salima', 'farida', 'malika', 'leila', 'nadia', 'assia', 'hanane',
            'iman', 'imene', 'amira', 'bouchra', 'hayat', 'houda', 'ilham', 'khalida',
            'lamia', 'linda', 'loubna', 'manel', 'mounia', 'nawel', 'nesrine', 'ouarda',
            'rabia', 'radia', 'rim', 'sabrina', 'safia', 'samia', 'sana', 'sihem', 'sonia',
            'soraya', 'yasmine', 'zahra', 'zineb'
        }
        MALE_NAMES = {
            'mohamed', 'ahmed', 'ali', 'brahim', 'omar', 'youssef', 'mustapha', 'khaled',
            'hassan', 'hocine', 'kamel', 'rachid', 'samir', 'mourad', 'abdelkader', 'said',
            'jamel', 'faycal', 'tarik', 'yacine', 'amine', 'karim', 'nabil', 'sofiane',
            'walid', 'hamza', 'bilal', 'redha', 'hakim', 'adel', 'hichem', 'mehdi',
            'salim', 'farid', 'lotfi', 'toufik', 'abderrahmane', 'abdallah', 'abdelaziz',
            'abdelhak', 'abdelkrim', 'abdelmadjid', 'abdenour', 'abderrazak', 'amar',
            'amir', 'anis', 'ayoub', 'aziz', 'bachir', 'badreddine', 'boualem', 'boubekeur',
            'chawki', 'cherif', 'djamel', 'el hadi', 'el hachemi', 'faouzi', 'fethi',
            'fouad', 'ghani', 'habib', 'halim', 'hamid', 'hicham', 'idriss', 'ilyes',
            'ismail', 'kaddour', 'khalil', 'lakhdar', 'larbi', 'lies', 'madjid', 'mahmoud',
            'malek', 'mammar', 'mehdi', 'miloud', 'mokhtar', 'mouloud', 'mounir', 'nacer',
            'nadir', 'nassim', 'nazim', 'nordine', 'noufel', 'othmane', 'rabah', 'rafik',
            'ramzi', 'reda', 'riad', 'riadh', 'salah', 'sami', 'sid ali', 'slimane',
            'tahar', 'tayeb', 'wahid', 'yassine', 'youcef', 'zakaria', 'zoubir'
        }

        contacts = Contact.objects.all()
        updated_count = 0
        
        for contact in contacts:
            original_sexe = contact.sexe
            new_sexe = None
            reason = ""

            # Normalize text for checking
            nom = (contact.nom or "").lower()
            prenom = (contact.prenom or "").lower()
            fonction = (contact.fonction or "").lower()
            full_text = f"{nom} {prenom} {fonction}"

            # 1. Check Titles (Priority)
            is_female_title = any(t in full_text for t in FEMALE_TITLES)
            is_male_title = any(t in full_text for t in MALE_TITLES)

            if is_female_title:
                new_sexe = 'FEMME'
                reason = "Title match (Female)"
            elif is_male_title:
                new_sexe = 'HOMME'
                reason = "Title match (Male)"
            
            # 2. Check Names (Secondary)
            if not new_sexe:
                # Check first name against dictionary
                # Split prenom to handle compound names, take first part
                prenom_stripped = prenom.strip() if prenom else ""
                first_name_part = prenom_stripped.split()[0] if prenom_stripped else ""
                
                if first_name_part in FEMALE_NAMES:
                    new_sexe = 'FEMME'
                    reason = f"Name match ({first_name_part})"
                elif first_name_part in MALE_NAMES:
                    new_sexe = 'HOMME'
                    reason = f"Name match ({first_name_part})"

            # 3. Apply Update
            if new_sexe and new_sexe != original_sexe:
                if dry_run:
                    self.stdout.write(f"[DRY RUN] ID {contact.id}: {contact.nom} {contact.prenom} ({original_sexe}) -> {new_sexe} [{reason}]")
                else:
                    contact.sexe = new_sexe
                    contact.save()
                    self.stdout.write(f"[UPDATED] ID {contact.id}: {contact.nom} {contact.prenom} -> {new_sexe} [{reason}]")
                updated_count += 1

        self.stdout.write(f"Done. Processed {contacts.count()} contacts. Updates proposed/made: {updated_count}")
