import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "etabibWebsite.settings")
django.setup()

from crm.models import Pays, Ville

countries = ["Morocco", "Tunisia", "Libya", "Egypt", "Saudi Arabia", "Maroc", "Tunisie", "Libye", "Egypte", "Arabie Saoudite", "Algérie", "Algeria"]

print("Checking Countries:")
for p in Pays.objects.all():
    print(f"ID: {p.id}, Nom: {p.nom}, Nom AR: {p.nom_ar}")

print("\nChecking Cities count per country:")
for p in Pays.objects.all():
    count = Ville.objects.filter(pays=p).count()
    print(f"Country: {p.nom} (ID: {p.id}) - Cities count: {count}")
