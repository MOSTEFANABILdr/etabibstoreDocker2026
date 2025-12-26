from allauth.account.models import EmailAddress
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Field
from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from validate_email import validate_email


class SignupFormStep1(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'placeholder': _("Tapez votre addresse e-mail")
    }))

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists() or EmailAddress.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "Vous vous êtes déjà inscrit avec cet e-mail, Veuillez plutôt vous connecter"
            )
        if not validate_email(email_address=email, check_format=True, check_dns=True, check_smtp=False):
            raise forms.ValidationError(
                _("L'adresse mail n'est pas valide!")
            )
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.form_show_labels = False
        self.helper.form_method = 'POST'
        btn_str = _("Envoyer")
        self.helper.layout = Layout(
            Field('email', css_class="etabib-form-control center-block"),
            HTML("<button type='submit' name='submit' class='btn btn-primary btn btn-etabib'>"
                 "<i class='fa fa-send'></i>" + str(btn_str) + "</button>")
        )

    def save(self):
        email = self.cleaned_data['email']
        with transaction.atomic():
            user = User()
            user.email = email
            password = User.objects.make_random_password()
            user.set_password(password)
            user.username = email
            user.save()

            mail = EmailAddress()
            mail.user = user
            mail.primary = True
            mail.verified = False
            mail.email = email
            mail.save()
        return (user, password)
