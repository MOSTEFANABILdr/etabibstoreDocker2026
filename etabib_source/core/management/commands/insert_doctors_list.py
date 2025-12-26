import csv
import os

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User, Group
from django.core.management import BaseCommand
from django.db import transaction
from post_office import mail

from core.enums import Role
from core.models import Medecin, Contact, CarteProfessionnelle
from etabibWebsite import settings


class Command(BaseCommand):
    help = 'Insert a list of doctors from a csv file. the file must be in the format nom,prenom,mail'

    def handle(self, *args, **options):
        nb = 0
        nbs = 0
        err = []
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'medecin_list.csv')
        with open(file_path) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=';')
            for row in readCSV:
                try:
                    with transaction.atomic():
                        nb += 1
                        nom = row[0]
                        prenom = row[1]
                        email = row[2]
                        mobile = row[3]
                        function = row[4]
                        addresse = row[5]
                        type_exercice = row[6]

                        if email == "benmendilped@gmail.com":
                            user = User.objects.get(email=email)
                            mot_de_passe = User.objects.make_random_password()
                            user.set_password(mot_de_passe)
                            user.save()
                        else:
                            #create a user
                            user = User()
                            user.first_name = nom
                            user.last_name = prenom
                            user.email = email
                            user.username = email
                            #generate random password
                            mot_de_passe = User.objects.make_random_password()
                            user.set_password(mot_de_passe)
                            user.save()

                            #create EmailAd
                            emailaddress = EmailAddress()
                            emailaddress.user = user
                            emailaddress.primary = True
                            emailaddress.verified = True
                            emailaddress.email = email
                            emailaddress.save()

                            #add the user to doctors group
                            group = Group.objects.get(name=Role.DOCTOR.value)
                            user.groups.add(group)

                            #create Medecin object
                            contact = Contact()
                            contact.nom = nom
                            contact.prenom = prenom
                            contact.email = email
                            contact.mdp_genere = mot_de_passe
                            contact.mobile = mobile
                            contact.fonction = function
                            contact.adresse = addresse
                            contact.save()

                            cp = CarteProfessionnelle()
                            cp.checked = True
                            cp.save()

                            medecin = Medecin()
                            medecin.user = user
                            medecin.contact = contact
                            medecin.carte = cp
                            medecin.save()

                            #send mail
                            mail.send(
                                email,
                                settings.DEFAULT_FROM_EMAIL,
                                template='participation_econgre',
                                context={
                                    'username': email,
                                    'password': mot_de_passe,
                                    'organiser_name': "HESPRO (Health & Science Provider)",
                                    'congress_name': "Les Premières Rencontres Algérienne de Pédiatrie Ambulatoires Rencontres CENTRE",
                                    'congress_date': "04 & 05 décembre 2020",
                                },
                                priority='high'
                            )
                        nbs += 1
                except Exception as ex:
                    err.append(nb)
                    print("Error %s" % ex)
        self.stdout.write(self.style.SUCCESS('Successfully added %s medecin,  from %s ' % (nbs, nb)))
        self.stdout.write(self.style.ERROR('Not added %s' % (err)))
