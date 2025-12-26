import csv
import os
import tempfile
from tempfile import NamedTemporaryFile

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User, Group
from django.core.management import BaseCommand
from django.db import transaction
from post_office import mail

from core.enums import Role
from core.models import Medecin, Contact, CarteProfessionnelle, Partenaire
from core.utils import generate_username
from etabibWebsite import settings


class Command(BaseCommand):
    help = 'Insert a list of partenaires from a csv file. the file must be in the format nom,prenom,mail'

    def handle(self, *args, **options):
        nb = 0
        nbs = 0
        err = []
        usersmdb = []
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'partenaire_list.csv')
        with open(file_path) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            for row in readCSV:
                try:
                    with transaction.atomic():
                        nb += 1
                        nom = row[0]
                        prenom = row[1]

                        # create a user
                        user = User()
                        user.first_name = nom
                        user.last_name = prenom
                        user.username = generate_username(nom, prenom)
                        # generate random password

                        mot_de_passe = User.objects.make_random_password()
                        user.set_password(mot_de_passe)
                        user.save()

                        # add the user to doctors group
                        group = Group.objects.get(name=Role.PARTNER.value)
                        user.groups.add(group)

                        # create Medecin object
                        contact = Contact()
                        contact.nom = nom
                        contact.prenom = prenom
                        contact.mdp_genere = mot_de_passe
                        contact.save()

                        partner = Partenaire()
                        partner.user = user
                        partner.contact = contact
                        partner.verifie = False
                        partner.save()

                        nbs += 1
                        usersmdb.append('nom : %s ,prenom : %s, Pseudo : %s, Mot de pass: %s ' % (nom, prenom, user.username, mot_de_passe))

                except Exception as ex:
                    err.append(nb)
                    print("Error %s" % ex)

            with open('FilePartnerList.txt', 'w') as filehandle:
                for line in usersmdb:
                    filehandle.write('%s\n' % line)

        self.stdout.write(self.style.SUCCESS('Successfully added %s Partenaire,  from %s ' % (nbs, nb)))
        self.stdout.write(self.style.ERROR('Not added %s' % (err)))
