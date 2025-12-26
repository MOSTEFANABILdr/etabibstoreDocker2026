import json
import os
from datetime import datetime

from django.core.management import BaseCommand
from django.db import transaction

from core.models import Contact, Specialite


class Command(BaseCommand):
    help = 'Insert a list of contacts from a json file'

    def try_parsing_date(self, text):
        for fmt in ('%d/%m/%Y', '%d/%m/%y', '%d-%m-%Y', '%d %m %y', '%d %B %Y'):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                pass
        print('no valid date format found %s' % text)

    def handle(self, *args, **options):
        nb = 0
        nbs = 0
        err = []
        characters_to_remove = "!()@-./"
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'contacts.json')
        with open(file_path) as jsonfile:
            datas = json.load(jsonfile)
            for data in datas["DOCC-JUIN-TRT"]:
                try:
                    with transaction.atomic():
                        nb += 1
                        nom = None if data["nom"] == "NULL" else data["nom"]
                        adresse = None if data["adresse"] == "NULL" else data["adresse"]
                        fixe = None if data["fixe"] == "NULL" else data["fixe"]
                        mobile = None if data["mobile"] == "NULL" else data["mobile"]
                        email = None if data["email"] == "NULL" else data["email"]
                        commentaire = None if data["commentaire"] == "NULL" else data["commentaire"]
                        specialite_id = None if data["speci_id"] == "NULL" else data["speci_id"]
                        fonction = None if data["fonction"] == "NULL" else data["fonction"]
                        departement = None if data["departement"] == "NULL" else data["departement"]
                        commune = None if data["commune"] == "NULL" else data["commune"]
                        codepostal = None if data["codepostal"] == "NULL" else data["codepostal"]
                        pageweb = None if data["pageweb"] == "NULL" else data["pageweb"]
                        facebook = None if data["facebook"] == "NULL" else data["facebook"]
                        instagram = None if data["instagram"] == "NULL" else data["instagram"]
                        linkedin = None if data["linkedin"] == "NULL" else data["linkedin"]
                        motif = None if data["motif"] == "NULL" else data["motif"]
                        source = None if data["source"] == "NULL" else data["source"]
                        type_exercice = None if data["type_exercice"] == "NULL" else data["type_exercice"]
                        twitter = None if data["twitter"] == "NULL" else data["twitter"]
                        gps = None if data["gps"] == "NULL" else data["gps"]
                        organisme = None if data["organisme"] == "NULL" else data["organisme"]
                        maps_url = None if data["maps_url"] == "NULL" else data["maps_url"]
                        place_id = None if data["place_id"] == "NULL" else data["place_id"]

                        contact = Contact()
                        contact.nom = nom
                        contact.adresse = adresse
                        contact.mobile = mobile
                        contact.fixe = fixe
                        contact.organisme = organisme
                        contact.type_exercice = type_exercice
                        contact.departement = departement
                        contact.fonction = fonction
                        contact.email = email

                        if specialite_id and specialite_id != "MEDECINE":
                            specialites = Specialite.objects.filter(id=specialite_id)
                            if not specialites.exists():
                                print("specialite does not exists: id=%s" % specialite_id)
                            else:
                                contact.specialite = specialites.first()

                        contact.source = source
                        contact.motif = motif
                        contact.linkedin = linkedin
                        contact.instagram = instagram
                        contact.facebook = facebook
                        contact.pageweb = pageweb
                        contact.commentaire = commentaire
                        contact.commune = commune
                        contact.codepostal = codepostal
                        contact.place_id = place_id
                        contact.maps_url = maps_url
                        contact.archive = False
                        contact.twitter = twitter
                        contact.gps = gps

                        contact.save()
                        nbs += 1
                except Exception as ex:
                    err.append(nb)
                    print("Error %s" % ex)
        self.stdout.write(self.style.SUCCESS('Successfully added %s contact, from %s ' % (nbs, nb)))
        self.stdout.write(self.style.ERROR('Not added %s' % (err)))
