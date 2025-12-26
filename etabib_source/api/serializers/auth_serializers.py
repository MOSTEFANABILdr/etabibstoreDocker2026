from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress
from allauth.account.utils import setup_user_email
from cities_light.models import Country, City
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.utils.translation import gettext as _
from drf_extra_fields.fields import Base64ImageField
from post_office import mail
from validate_email import validate_email
from rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers

from core.enums import Role
from core.models import Patient, Specialite, Contact, ProfessionnelSante, CarteProfessionnelle
from etabibWebsite import settings


class PatientRegisterSerializer(RegisterSerializer):
    GENDER_CHOICES = (
        ("1", "HOMME"),
        ("2", "FEMME")
    )
    username = None
    first_name = serializers.CharField(required=True, write_only=True)
    last_name = serializers.CharField(required=True, write_only=True)
    birth_date = serializers.DateField(required=True, write_only=True)
    sexe = serializers.ChoiceField(choices=GENDER_CHOICES, required=True)
    phone = serializers.CharField(required=True, write_only=True)

    def get_cleaned_data(self):
        return {
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
            'birth_date': self.validated_data.get('birth_date', ''),
            'phone': self.validated_data.get('phone', ''),
            'sexe': self.validated_data.get('sexe', ''),
        }

    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        adapter.save_user(request, user, self)
        setup_user_email(request, user, [])
        user.save()
        patient = Patient()
        patient.user = user
        patient.user.first_name = self.cleaned_data['first_name']
        patient.user.last_name = self.cleaned_data['last_name']
        patient.date_naissance = self.cleaned_data['birth_date']
        patient.sexe = self.cleaned_data['sexe']
        patient.telephone = self.cleaned_data['phone']
        patient.user.groups.clear()
        if patient.user.groups.count() == 0:
            patient.user.groups.add(Group.objects.get(name=Role.PATIENT.value))

        patient.user.save()
        patient.save()
        return user


class RegisterFromInstallerSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    nom = serializers.CharField(required=True)
    prenom = serializers.CharField(required=True)
    sexe = serializers.CharField(required=True)
    specialite = serializers.IntegerField(required=True)
    mobile = serializers.CharField(required=True)
    fix = serializers.CharField(required=False)
    pays = serializers.IntegerField(required=False)
    ville = serializers.IntegerField(required=False)
    carte_professionnelle = Base64ImageField(required=True)
    type_exercice = serializers.CharField(required=True)
    date_debut_exercice = serializers.DateField(required=True, format="%d-%m-%Y", input_formats=['%d-%m-%Y', 'iso-8601'])

    def validate_specialite(self, specialite):
        if not Specialite.objects.filter(pk=specialite).exists():
            raise serializers.ValidationError("Specialite id is not valid")
        return specialite

    def validate_pays(self, pays):
        if not Country.objects.filter(pk=pays).exists():
            raise serializers.ValidationError("pays id is not valid")
        return pays

    def validate_ville(self, ville):
        if not City.objects.filter(pk=ville).exists():
            raise serializers.ValidationError("ville id is not valid")
        return ville

    def validate_email(self, email):
        if User.objects.filter(email=email).exists() or EmailAddress.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                _("Vous vous êtes déjà inscrit avec cet e-mail, Veuillez plutôt vous connecter")
            )
        if not validate_email(email_address=email, check_format=True, check_dns=True, check_smtp=False):
            raise serializers.ValidationError(
                _("L'adresse mail n'est pas valide!")
            )
        return email

    def save(self, request=None):
        email = self.validated_data.get('email', None)
        nom = self.validated_data.get('nom', None)
        prenom = self.validated_data.get('prenom', None)
        specialite = self.validated_data.get('specialite', None)
        mobile = self.validated_data.get('mobile', None)
        fixe = self.validated_data.get('fix', None)
        pays = self.validated_data.get('pays', None)
        ville = self.validated_data.get('ville', None)
        carte_professionnelle = self.validated_data.get('carte_professionnelle', None)
        type_exercice = self.validated_data.get('type_exercice', None)
        date_debut_exercice = self.validated_data.get('date_debut_exercice', None)
        sexe = self.validated_data.get('sexe', None)

        with transaction.atomic():
            contact = Contact()
            user = User()

            password = User.objects.make_random_password()

            contact.nom = nom
            contact.prenom = prenom
            contact.mdp_genere = password
            contact.email = email
            contact.mobile = mobile
            contact.fixe = fixe
            contact.specialite = Specialite.objects.get(id=specialite)
            if pays:
                contact.pays = Country.objects.get(id=pays)
            if ville:
                contact.ville = City.objects.get(id=ville)
            contact.carte = carte_professionnelle
            contact.date_debut_exercice = date_debut_exercice
            contact.type_exercice = type_exercice
            if sexe == "0":
                contact.sexe = Contact.GENDER_CHOICES[0][0]
            elif sexe == "1":
                contact.sexe = Contact.GENDER_CHOICES[1][0]

            user.first_name = nom
            user.last_name = prenom
            user.set_password(password)
            user.username = email
            user.email = email

            contact.save()
            user.save()

            user.groups.add(Group.objects.get(name=Role.VISITOR.value))

            email_add = EmailAddress()
            email_add.user = user
            email_add.primary = True
            email_add.verified = True
            email_add.email = email
            email_add.save()

            carte_pro = CarteProfessionnelle()
            carte_pro.image = carte_professionnelle
            carte_pro.save()

            pro = ProfessionnelSante()
            pro.user = user
            pro.contact = contact
            pro.carte = carte_pro

            pro.save()

            to = [user.email]
            from_email = "eTabib <{}>".format(settings.EMAIL_HOST_USER)
            mail.send(
                to,
                from_email,
                template='installer_registration',
                context={
                    "username": user.email,
                    "password": password,
                    "login_link": "{}://{}".format(request.scheme, request.get_host())
                },
            )
