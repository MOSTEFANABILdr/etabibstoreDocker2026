from dal import autocomplete
from django import forms
from django.contrib.admin import widgets
from django.utils.translation import ugettext_lazy as _

from core.models import OffrePrepaye
from . import settings
from .models import Coupon, CouponUser, Campaign
from .settings import COUPON_TYPES, COUPON_TARGETS


class CouponGenerationForm(forms.Form):
    quantity = forms.IntegerField(label=_("Quantity"))
    value = forms.IntegerField(label=_("Value"), required=False)
    type = forms.ChoiceField(label=_("Type"), choices=COUPON_TYPES)
    target = forms.ChoiceField(label=_("Target"), choices=COUPON_TARGETS)
    offer = forms.ModelChoiceField(
        required=False,
        label=_('Offer'),
        queryset=OffrePrepaye.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='offre-prepaye-autocomplete',
            attrs={
                'data-placeholder': _('Séléctionnez une Offre ...'),
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )
    valid_until = forms.SplitDateTimeField(
        label=_("Valid until"), required=False,
        help_text=_("Leave empty for coupons that never expire")
    )
    prefix = forms.CharField(label="Prefix", required=False)
    campaign = forms.ModelChoiceField(
        label=_("Campaign"), queryset=Campaign.objects.all(), required=False
    )

    def clean(self):
        type = self.cleaned_data['type']
        offer = self.cleaned_data['offer']
        value = self.cleaned_data['value']
        target = self.cleaned_data['target']
        if type == settings.COUPON_TYPES[2][0]:#"sponsorship"
            if target != "1":#abonnement
                raise forms.ValidationError(_("Type 'sponsorship' can be used with Target 'abonnement'"))
            if offer:
                self.cleaned_data['value'] = offer.id
            else:
                raise forms.ValidationError(_("Offer must not be null"))
        else:
            if not value:
                raise forms.ValidationError(_("Value must not be null"))
        return self.cleaned_data


    def __init__(self, *args, **kwargs):
        super(CouponGenerationForm, self).__init__(*args, **kwargs)
        self.fields['valid_until'].widget = widgets.AdminSplitDateTime()


class CouponForm(forms.Form):
    code = forms.CharField(label=_("Coupon code"))

    def __init__(self, *args, **kwargs):
        self.user = None
        self.types = None
        if 'user' in kwargs:
            self.user = kwargs.pop('user')
        if 'types' in kwargs:
            self.types = kwargs.pop('types')
        super(CouponForm, self).__init__(*args, **kwargs)

    def clean_code(self):
        code = self.cleaned_data['code']
        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            raise forms.ValidationError(_("This code is not valid."))
        self.coupon = coupon

        # Updated comparison: use != instead of "is not"
        if self.user is None and coupon.user_limit != 1:
            raise forms.ValidationError(_(
                "The server must provide a user to this form to allow you to use this code. Maybe you need to sign in?"
            ))

        if coupon.is_redeemed:
            raise forms.ValidationError(_("This code has already been used."))

        try:  # check if there is a user-bound coupon existing
            user_coupon = coupon.users.get(user=self.user)
            if user_coupon.redeemed_at is not None:
                raise forms.ValidationError(_("This code has already been used by your account."))
        except CouponUser.DoesNotExist:
            if coupon.user_limit != 0:  # Updated comparison: zero means no limit of user count
                # Only user-bound coupons left, and you don't have one
                if coupon.user_limit == coupon.users.filter(user__isnull=False).count():
                    raise forms.ValidationError(_("This code is not valid for your account."))
                if coupon.user_limit == coupon.users.filter(redeemed_at__isnull=False).count():
                    raise forms.ValidationError(_("This code has already been used."))

        if self.types is not None and coupon.type not in self.types:
            raise forms.ValidationError(_("This code is not meant to be used here."))
        if coupon.expired():
            raise forms.ValidationError(_("This code is expired."))
        return code