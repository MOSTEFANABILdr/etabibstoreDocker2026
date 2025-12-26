import csv
import os
from datetime import datetime, timedelta

import pytz
from allauth.account.models import EmailAddress
from cities_light.models import Country, City
from django.contrib.auth.models import User, Group
from django.core.management import BaseCommand
from django.db import transaction
from django.utils import timezone
from post_office import mail
from validate_email import validate_email

from core.enums import Role
from core.models import Medecin, Contact, CarteProfessionnelle, ProfessionnelSante, Specialite
from etabibWebsite import settings


class Command(BaseCommand):
    help = 'Insert a list of doctors from a csv file.'

    def try_parsing_date(self, text):
        for fmt in ('%d/%m/%Y', '%d/%m/%y', '%d-%m-%Y',  '%d %m %y', '%d %B %Y'):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                pass
        print('no valid date format found %s' % text)

    def handle(self, *args, **options):
        nb = 0
        nbs = 0
        nbss = 0
        nbe = 0
        nbp = 0
        err = []
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'simem_contact.csv')
        with open(file_path) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            for row in readCSV:
                try:
                    with transaction.atomic():
                        nb += 1
                        id = row[0]
                        nom = row[1]
                        prenom = row[2]
                        ville = row[3]
                        pays = row[4]
                        fonction = row[5]
                        organisme = row[6]
                        profile = row[7]
                        mobile = row[8]
                        specialite = row[9]
                        sexe = row[10]
                        type_struct = row[11]
                        type_exercice = row[12]
                        origine = row[13]
                        adresse = row[14]
                        departement = row[15]
                        fix = row[16]
                        addr_postal = row[17]
                        zones = row[18]
                        fax = row[19]
                        aff_phone_number = row[20]
                        date_naiss = row[21]
                        email = row[22]

                        email_is_valid = validate_email(email)
                        if email and origine == "SIMEM21":
                            if email_is_valid:
                                if Contact.objects.filter(nom__iexact=nom, prenom__iexact=prenom).exists() or User.objects.filter(email=email).exists():
                                    nbe += 1
                                else:
                                    # create a user
                                    user = User()
                                    user.first_name = nom
                                    user.last_name = prenom
                                    user.email = email
                                    user.username = email
                                    # generate random password
                                    mot_de_passe = User.objects.make_random_password()
                                    user.set_password(mot_de_passe)
                                    user.save()

                                    # create EmailAd
                                    emailaddress = EmailAddress()
                                    emailaddress.user = user
                                    emailaddress.primary = True
                                    emailaddress.verified = False
                                    emailaddress.email = email
                                    emailaddress.save()

                                    # create Contact object
                                    contact = Contact()
                                    contact.nom = nom
                                    contact.sexe = Contact.GENDER_CHOICES[0][0] if sexe == "H" else Contact.GENDER_CHOICES[1][0] if sexe == "F" else None
                                    if date_naiss:
                                        d = self.try_parsing_date(date_naiss)
                                        if d:
                                            contact.date_naissance = d.date()
                                    if specialite:
                                        specialites = Specialite.objects.filter(libelle=specialite)
                                        if not specialites.exists():
                                            print("specialite does not exists: %s" % specialite)
                                        else:
                                            contact.specialite = specialites.first()

                                    if type_exercice:
                                        contact.type_exercice = "8" if type_exercice == "PRIVE" else "6" if type_exercice == "PUBLIC" else "7"
                                    contact.prenom = prenom
                                    contact.email = email
                                    contact.mdp_genere = mot_de_passe
                                    contact.mobile = mobile
                                    contact.fixe = fix
                                    contact.source = "14" if origine == "SIMEM21" else "15" if origine == "LISTE FOSC" else None
                                    if pays:
                                        if pays in ["ALGERIA", "ALGERIE"]:
                                            c = Country.objects.get(code2="DZ")
                                            contact.pays = c
                                        elif pays in ["Angola"]:
                                            c = Country.objects.get(code2="AO")
                                            contact.pays = c
                                        elif pays in ["South Korea"]:
                                            c = Country.objects.get(code2="KP")
                                            contact.pays = c
                                        elif pays in ["France"]:
                                            c = Country.objects.get(code2="FR")
                                            contact.pays = c
                                        elif pays in ["india"]:
                                            c = Country.objects.get(code2="IN")
                                            contact.pays = c
                                        elif pays in ["Pakistan"]:
                                            c = Country.objects.get(code2="PK")
                                            contact.pays = c
                                        elif pays in ["United Arab Emirates"]:
                                            c = Country.objects.get(code2="AE")
                                            contact.pays = c

                                    if ville:
                                        v = ville.split("-")[0]
                                        citiess = City.objects.filter(name=v)
                                        if citiess.exists():
                                            contact.ville = citiess.first()
                                        else:
                                            print("city does not exists: %s" % v)

                                    contact.fonction = fonction
                                    contact.organisme = organisme
                                    contact.departement = departement
                                    contact.adresse = adresse
                                    contact.type_structure = type_struct
                                    contact.save()

                                    pro = ProfessionnelSante()
                                    pro.user = user
                                    pro.contact = contact
                                    pro.save()
                                    pro.user.groups.add(Group.objects.get(name=Role.VISITOR.value))

                                    # send mail
                                    rnb = nbs // 100
                                    scheduled_time = (timezone.now() + timedelta(days=rnb)).date()
                                    # tz = pytz.timezone('Africa/Algiers')
                                    # scheduled_time = scheduled_time.replace(tzinfo=tz)
                                    mail.send(
                                        user.email,
                                        settings.DEFAULT_FROM_EMAIL,
                                        template='expo_registration',
                                        context={
                                            'username': user.email,
                                            'password': mot_de_passe,
                                            'login_link': "https://store.etabib.dz/login"
                                        },
                                        priority='low',
                                        scheduled_time=scheduled_time
                                    )
                                    nbs += 1
                            else:
                                print("email is not valid: %s" % email)
                                nbp += 1
                        else:
                            if Contact.objects.filter(nom__iexact=nom, prenom__iexact=prenom).exists():
                                nbe += 1
                            else:
                                # create Contact object
                                contact = Contact()
                                contact.nom = nom
                                contact.sexe = Contact.GENDER_CHOICES[0][0] if sexe == "H" else Contact.GENDER_CHOICES[1][0]
                                if date_naiss:
                                    d = self.try_parsing_date(date_naiss)
                                    if d:
                                        contact.date_naissance = d.date()
                                if specialite:
                                    specialites = Specialite.objects.filter(libelle=specialite)
                                    if not specialites.exists():
                                        print("specialite does not exists: %s" % specialite)
                                    else:
                                        contact.specialite = specialites.first()

                                if type_exercice:
                                    contact.type_exercice = "8" if type_exercice == "PRIVE" else "6" if type_exercice == "PUBLIC" else "7"
                                contact.prenom = prenom
                                contact.email = email
                                contact.mobile = mobile
                                contact.fixe = fix
                                contact.source = "14" if origine == "SIMEM21" else "15" if origine == "LISTE FOSC" else None
                                if pays:
                                    if pays in ["Algeria", "ALGERIE"]:
                                        c = Country.objects.get(code2="DZ")
                                        contact.pays = c
                                    elif pays in ["angola"]:
                                        c = Country.objects.get(code2="AO")
                                        contact.pays = c
                                    elif pays in ["coree"]:
                                        c = Country.objects.get(code2="KP")
                                        contact.pays = c
                                    elif pays in ["france"]:
                                        c = Country.objects.get(code2="FR")
                                        contact.pays = c
                                    elif pays in ["inde"]:
                                        c = Country.objects.get(code2="IN")
                                        contact.pays = c
                                    elif pays in ["Pakistan"]:
                                        c = Country.objects.get(code2="PK")
                                        contact.pays = c
                                    elif pays in ["UAE"]:
                                        c = Country.objects.get(code2="AE")
                                        contact.pays = c

                                if ville:
                                    v = ville.split("-")[0]
                                    citiess = City.objects.filter(name=v)
                                    if citiess.exists():
                                        contact.ville = citiess.first()
                                    else:
                                        print("city does not exists: %s" % v)

                                contact.fonction = fonction
                                contact.organisme = organisme
                                contact.departement = departement
                                contact.adresse = adresse
                                contact.type_structure = type_struct
                                contact.save()
                                nbss += 1
                except Exception as ex:
                    err.append(nb)
                    print("Error %s" % ex)
        self.stdout.write(self.style.SUCCESS('Successfully added %s Professionnals, %s contact,  from %s ' % (nbs, nbss, nb)))
        self.stdout.write(self.style.ERROR('Duplicated %s' % (nbe)))
        self.stdout.write(self.style.ERROR('email not valid %s' % (nbp)))
        self.stdout.write(self.style.ERROR('Not added %s' % (err)))
