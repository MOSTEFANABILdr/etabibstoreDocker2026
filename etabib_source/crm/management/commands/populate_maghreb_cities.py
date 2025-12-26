import re
from django.core.management.base import BaseCommand
from cities_light.models import City, Region, Country
from crm.models import Ville, Wilaya, Pays
from django.db import transaction

class Command(BaseCommand):
    help = 'Populate Ville model with cities from Maghreb, Egypt, and Saudi Arabia'

    def get_arabic_name(self, name, alternate_names):
        if not alternate_names:
            return name
        
        # Split alternate names
        alts = alternate_names.split(';')
        
        # Regex for Arabic characters
        arabic_pattern = re.compile(r'[\u0600-\u06FF]')
        
        # Find first name with Arabic characters
        for alt in alts:
            if arabic_pattern.search(alt):
                return alt
        
        # Fallback to first alternate or original name
        return alts[0] if alts else name

    def is_arabic(self, text):
        if not text:
            return False
        return bool(re.search(r'[\u0600-\u06FF]', text))

    def handle(self, *args, **options):
        target_countries = {
            'TN': 'Tunisia',
            'MA': 'Morocco',
            'LY': 'Libya',
            'MR': 'Mauritania',
            'EG': 'Egypt',
            'SA': 'Saudi Arabia'
        }

        with transaction.atomic():
            for code, name in target_countries.items():
                self.stdout.write(f'Processing {name}...')
                
                # Get or create Pays
                try:
                    country = Country.objects.get(code2=code)
                except Country.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'Country {name} not found in cities_light. Skipping.'))
                    continue

                pays, created = Pays.objects.get_or_create(
                    nom=country.name,
                    defaults={'nom_ar': self.get_arabic_name(country.name, country.alternate_names)}
                )

                # Process Regions as Wilayas
                regions = Region.objects.filter(country=country)
                for region in regions:
                    wilaya, created = Wilaya.objects.get_or_create(
                        nom=region.name,
                        pays=pays,
                        defaults={'nom_ar': self.get_arabic_name(region.name, region.alternate_names)}
                    )

                    # Process Cities
                    cities = City.objects.filter(region=region)
                    for city in cities:
                        nom_ar = self.get_arabic_name(city.name, city.alternate_names)
                        
                        # Try to find existing Ville (case-insensitive match due to collation)
                        ville = Ville.objects.filter(
                            nom=city.name,
                            wilaya=wilaya,
                            pays=pays
                        ).first()

                        if ville:
                            # Update logic: Prefer Arabic names
                            should_update = False
                            if self.is_arabic(nom_ar):
                                should_update = True
                            elif not self.is_arabic(ville.nom_ar):
                                should_update = True
                            
                            if should_update:
                                ville.nom_ar = nom_ar
                                ville.latitude = city.latitude
                                ville.longitude = city.longitude
                                ville.cl_map = city
                                ville.save()
                        else:
                            Ville.objects.create(
                                nom=city.name,
                                wilaya=wilaya,
                                pays=pays,
                                nom_ar=nom_ar,
                                latitude=city.latitude,
                                longitude=city.longitude,
                                cl_map=city
                            )
        
        self.stdout.write(self.style.SUCCESS('Successfully populated cities.'))
