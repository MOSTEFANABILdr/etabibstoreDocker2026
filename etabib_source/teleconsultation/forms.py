from allauth.account.models import EmailAddress
from bootstrap_datepicker_plus import DatePickerInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, HTML, Div, Fieldset, Row, Column
from dal import autocomplete
from django import forms
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.forms import NumberInput, DateInput, TextInput
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django_toggle_switch_widget.widgets import DjangoToggleSwitchWidget
from validate_email import validate_email

from core.enums import Role
from core.models import Specialite, Patient, CarteID
from core.utils import generate_username
from core.widgets import CustomAutoCompleteWidgetSingle
from coupons.models import Coupon
from teleconsultation.models import Treclamation


class PatientSearchForm(forms.Form):
    patient = forms.ModelChoiceField(
        label=_('Recherche'),
        queryset=Patient.objects.filter(),
        widget=CustomAutoCompleteWidgetSingle(
            url='recently-patient-autocomplete',
            attrs={
                'data-placeholder': _('Choisir une patient ...'),
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super(PatientSearchForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False


class ClaimCreateForm(forms.ModelForm):
    class Meta:
        model = Treclamation
        fields = ['message']

    def __init__(self, *args, **kwargs):
        super(ClaimCreateForm, self).__init__(*args, **kwargs)


class ClaimUpdateForm(forms.ModelForm):
    class Meta:
        model = Treclamation
        fields = ['message', 'reponse']

    def __init__(self, *args, **kwargs):
        self.reponse_read_only = kwargs.pop('reponse_read_only', None)
        super(ClaimUpdateForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.id:
            self.fields['message'].widget.attrs['readonly'] = True
        if self.reponse_read_only or self.reponse_read_only == None:
            self.fields['reponse'].widget.attrs['readonly'] = True


class SearchDoctorForm(forms.Form):
    CHOICES = (
        ('0', _('FEMME')),
        ('1', _('HOMME')),
        ('2', _('Tout')),
    )
    specialty = forms.ModelChoiceField(
        required=False,
        queryset=Specialite.objects.all(),
        widget=autocomplete.ModelSelect2
        (url='speciality-autocomplete',
         attrs={'data-placeholder': _('Choisir une spécialité ...'),
                'data-theme': 'bootstrap',
                'data-html': True}
         )
    )

    query = forms.CharField(label='', max_length=255, required=False,
                            widget=forms.TextInput(attrs={'placeholder': _('Nom ou prénom')}))
    gender = forms.ChoiceField(choices=CHOICES, required=False,
                               widget=forms.RadioSelect)
    care_team = forms.BooleanField(
        label=_("Mon équipe de soins"),
        required=False
    )

    class Meta:
        unlabelled_fields = ('query', 'gender', "specialty")

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_show_labels = True
        text = _("Filtrer")
        self.helper.layout = Layout(
            Field('query', css_class=''),
            Field('specialty', css_class=''),
            Field('gender', css_class=''),
            Field('care_team', css_class=""),
            HTML('<button id="btn-filter" type="submit" class="btn btn-etabib mg-l-15">'
                 '<span class="fa fa-search"></span> %s' % text +
                 '</button>')
        )
        super(SearchDoctorForm, self).__init__(*args, **kwargs)
        for field in self.Meta.unlabelled_fields:
            self.fields[field].label = False


class SearchPatientForm(forms.Form):
    CHOICES = (
        ('1', _('HOMME')),
        ('0', _('FEMME')),
        ('2', _('Tout')),
    )
    query = forms.CharField(label='', max_length=255, required=False,
                            widget=forms.TextInput(attrs={'placeholder': _('Nom ou prénom')}))
    gender = forms.ChoiceField(choices=CHOICES, required=False,
                               widget=forms.RadioSelect)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'POST'
        self.helper.form_show_labels = False
        self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        text = _("Filtrer")
        self.helper.layout = Layout(
            Field('query', css_class='mg-r-15 input-lg'),
            Field('gender', css_class='i-checks'),
            HTML('<button id="btn-filter" type="submit" class="btn btn-etabib mg-l-15">'
                 '<span class="fa fa-search"></span> %s' % text +
                 '</button>')
        )
        super(SearchPatientForm, self).__init__(*args, **kwargs)


class UseCouponForm(forms.Form):
    coupon = forms.CharField(label=_("Code promo"), widget=forms.TextInput(attrs={
        'placeholder': _("Tapez le code")
    }))

    def clean_coupon(self):
        code = self.cleaned_data['coupon']
        try:
            self.coupon = Coupon.objects.get(code=code, target="2")  # target see COUPON_TARGETS settings
            coupon_user = self.coupon.users.filter(user=self.patient.user)
            if self.coupon.is_redeemed or self.coupon.expired() or coupon_user.exists():
                raise forms.ValidationError(_("Coupon invalide!"))
        except Coupon.DoesNotExist:
            raise forms.ValidationError(_("Coupon invalide!"))
        return code

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        self.patient = kwargs.pop("patient", None)
        super(UseCouponForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        self.coupon.redeem(user=self.patient.user)


class AddPatientForm(forms.ModelForm):
    nom = forms.CharField(label=_('Nom'), max_length=255)
    prenom = forms.CharField(label=_('Prénom'), max_length=255)

    class Meta:
        model = Patient
        fields = ['nom', 'prenom', 'date_naissance', 'nin', 'num_carte_id', 'chifa', 'telephone', 'sexe']
        widgets = {
            'date_naissance': DatePickerInput(
                format="%Y-%m-%d",
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                }
            ),
        }

    def clean_nin(self):
        nin = self.cleaned_data['nin']
        if nin:
            if Patient.objects.filter(nin=nin).exists():
                raise forms.ValidationError(
                    _("Vous vous êtes déjà inscrit avec ce numéro national")
                )
        return nin

    def clean_num_carte_id(self):
        num_carte_id = self.cleaned_data['num_carte_id']
        if num_carte_id:
            if Patient.objects.filter(num_carte_id=num_carte_id).exists():
                raise forms.ValidationError(
                    _("Vous vous êtes déjà inscrit cette carte")
                )
        return num_carte_id

    def clean_chifa(self):
        chifa = self.cleaned_data['chifa']
        if chifa:
            if Patient.objects.filter(chifa=chifa).exists():
                raise forms.ValidationError(
                    _("Vous vous êtes déjà inscrit avec cette carte chifa")
                )
        return chifa

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.request = kwargs.pop('request', None)
        self.helper.form_id = "addPatientForm1"
        self.helper.form_method = 'POST'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-3'
        self.helper.field_class = 'col-lg-9'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(Div("nom", css_class='col-6'), Div("prenom", css_class='col-6'), css_class="row"),
            Div(Div("num_carte_id", css_class='col-6'), Div("chifa", css_class='col-6'), css_class="row"),
            Div(Div("nin", css_class='col-6'), Div("sexe", css_class='col-6'), css_class="row"),
            Div(Div("telephone", css_class='col-6'), Div("date_naissance", css_class='col-6'), css_class="row"),
        )
        super(AddPatientForm, self).__init__(*args, **kwargs)
        self.fields['telephone'].required = True

    def save(self, commit=True):
        patient = super(AddPatientForm, self).save(commit=False)
        with transaction.atomic():
            user = User()
            user.first_name = self.cleaned_data.get('nom')
            user.last_name = self.cleaned_data.get('prenom')
            password = User.objects.make_random_password()
            user.set_password(password)
            user.username = generate_username(slugify(
                user.first_name, allow_unicode=True), slugify(user.last_name, allow_unicode=True)
            )
            user.email = f'{user.username}@ibnhamza.com'
            user.save()
            patient.user = user
            user.groups.add(Group.objects.get(name=Role.PATIENT.value))
            email = EmailAddress()
            email.user = user
            email.email = user.email
            email.primary = True
            email.verified = False
            email.save()
            patient.save()
            context = {'patient': patient, 'password': password}
        return context


class CarteIDForm(forms.Form):
    carte_id_f = forms.FileField(required=False, label=_('وجه البطاقة الذي فيه الصورة'),
                                 widget=forms.FileInput({'data-js-image-input': '', 'accept': 'image/*'}))
    carte_id_p = forms.FileField(required=False, label=_('ظهر البطاقة'),
                                 widget=forms.FileInput({'data-js-image-input1': '', 'accept': 'image/*'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                HTML("""
                <ul class="nav nav-progress" style="flex-direction:row !important">
                   <li><a class="nav-link" href="#step-1"> تحميل البطاقة </a></li>
                   <li><a class="nav-link" href="#step-2"> تعديل صورة وجه البطاقة </a></li>
                   <li><a class="nav-link" href="#step-2"> تعديل صورة ظهر البطاقة </a></li>
                   <li><a class="nav-link" href="#step-3"> معالجة الصورة </a></li>
                </ul>
                {{ form.errors }}
                {{ form.non_field_errors }}
                """),
                Div(
                    Div(
                        Fieldset(
                            _("<br>قم بتحميل بطاقة التعريف البيومترية"),
                            'carte_id_f',
                            'carte_id_p',
                        ),
                        css_id="step-1", css_class="tab-pane"),
                    Div(
                        HTML("<div class='image-container' data-js-image-container></img></div>"),
                        css_id="step-2", css_class="tab-pane"),
                    Div(
                        HTML("<div class='image-container' data-js-image-container1></img></div>"),
                        css_id="step-3", css_class="tab-pane"),
                    Div(
                        Fieldset(
                            _("جار تحميل صور البطاقة"),
                        css_id='step-upload'),
                        HTML("""
                        <div id="upload_progress" class="progress progress-sm rounded-corner m-b-5">
                            <div class="progress-bar progress-bar-striped progress-bar-animated bg-orange f-s-10 f-w-600" 
                                style="width: 0%;"></div>
                        </div>
                        """),
                        css_id="step-4", css_class="tab-pane"),
                    css_class="tab-content",
                ),
                css_id="smartwizard"
            )
        )
