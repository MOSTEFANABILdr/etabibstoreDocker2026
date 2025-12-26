import logging
from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import Contact

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean core.contact table from unwanted records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be done without changing data',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        self.stdout.write(f"Starting contact cleaning process (Dry Run: {dry_run})...")

        unwanted_keywords = [
            # Services
            "lavage", "washing", "car wash", "coiffure", "coiffeur", "barber", "halls", "fêtes", "wedding", 
            "traiteur", "catering", "restaurant", "café", "coffee", "pizzeria", "fast food", "hotel", "motel", 
            "auberge", "voyage", "travel", "agence", "immobilier", "real estate", "auto", "moto", "école", 
            "school", "crèche", "lycée", "université", "university", "formation", "training", "gym", "sport", 
            "fitness", "piscine", "pool", "bain", "hammam", "sauna", "spa", "beauté", "beauty", "cosmétique", 
            "parfumerie", "vêtement", "clothing", "boutique", "shop", "supermarché", "market", 
            "boucherie", "boulangerie", "patisserie", "meuble", "furniture", "informatique", "computer", 
            "cyber", "phone", "mobile", "réparation", "repair", "plombier", "electricien", "menuisier", 
            "peintre", "construction", "travaux", "transport", "taxi", "vtc", "location", "rental",
            
            # Arabic
            "حلاق", "غسيل", "سيارات", "مقهى", "مطعم", "فندق", "وكالة", "مدرسة", "جامعة", "تكوين", 
            "رياضة", "مسبح", "حمام", "تجميل", "ملابس", "محل", "سوق", "جزار", "مخبزة", "حلويات", 
            "أثاث", "إعلام آلي", "هاتف", "تصليح", "نقل", "كراء"
        ]

        wanted_keywords = [
            "dr", "docteur", "medecin", "médecin", "clinique", "clinic", "hopital", "hospital", 
            "pharmacie", "pharmacy", "laboratoire", "laboratory", "analyse", "radiologie", "imagerie", 
            "dentiste", "dentist", "orthophoniste", "kine", "kiné", "physio", "infirmier", "nurse", 
            "sage-femme", "midwife", "optien", "optician", "audio", "psych", "nutrition", "diet", 
            "vet", "vétérinaire", "ambiance", "paramedical", "cabinet", "medical", "médical", "soin", "care",
            "sanitaire", "ambulance", "pharmaceutique",
            # Arabic Whitelist
            "دكتور", "طبيب", "عيادة", "مستشفى", "صيدلية", "مخبر", "مركز", "علاج", "صحة", "جراحة"
        ]

        # Fetch active contacts
        contacts = Contact.objects.filter(archive=False)
        count = 0
        archived_count = 0

        for contact in contacts:
            count += 1
            if count % 1000 == 0:
                self.stdout.write(f"Scanned {count} contacts...")

            # Construct full text for search
            text_parts = [
                contact.nom,
                contact.prenom,
                contact.fonction,
                contact.organisme,
                contact.commentaire
            ]
            full_text = " ".join([str(p).lower() for p in text_parts if p])

            # Check for unwanted keywords
            found_unwanted = None
            for keyword in unwanted_keywords:
                if keyword in full_text:
                    found_unwanted = keyword
                    break
            
            if found_unwanted:
                # Safety Check: Check for wanted keywords to avoid false positives
                is_safe = False
                for safe_word in wanted_keywords:
                    if safe_word in full_text:
                        is_safe = True
                        break
                
                if not is_safe:
                    archived_count += 1
                    msg = f"Archiving: {contact.id} - {contact.full_name} (Matched: {found_unwanted})"
                    self.stdout.write(msg)
                    
                    if not dry_run:
                        contact.archive = True
                        if contact.nom and not contact.nom.startswith("[TO_VERIFY]"):
                            contact.nom = f"[TO_VERIFY] {contact.nom}"
                        elif not contact.nom:
                             contact.nom = "[TO_VERIFY] Unknown"
                        contact.save()

        self.stdout.write(self.style.SUCCESS(f"Finished. Scanned: {count}. Archived: {archived_count}"))
