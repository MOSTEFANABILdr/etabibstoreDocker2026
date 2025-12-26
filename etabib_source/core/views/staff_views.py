from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from formtools.wizard.views import SessionWizardView

from core.forms.staff_forms import ChnageOfferForm1, ChnageOfferFormSet, ChangePointsForm1, ChangePointsForm2
from core.models import Facture_OffrePrep_Licence, Medecin


class ChangeOfferWizard(SessionWizardView):
    form_list = [ChnageOfferForm1, ChnageOfferFormSet]
    template_name = "admin/offre_change_admin.html"

    @method_decorator(login_required)
    @method_decorator(staff_member_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, step=None, data=None, files=None):
        form = super(ChangeOfferWizard, self).get_form(step, data, files)

        # Determine the step if not given
        if step is None:
            step = self.steps.current
        if step == '1':
            # Return number of forms for formset requested
            # in previous step.
            userchoice = self.get_cleaned_data_for_step('0')
            medecin = userchoice['medecin']
            fols = Facture_OffrePrep_Licence.objects.filter(facture__medecin=medecin)
            formset = ChnageOfferFormSet(initial=[{'fol': fol} for fol in fols], data=data)
            formset.max_num = fols.count()
            return formset
        return form

    def done(self, form_list, **kwargs):
        for fitem in form_list:
            if isinstance(fitem, ChnageOfferFormSet):
                for form in fitem:
                    form.save()
            else:
                fitem.save()

        messages.success(self.request, "Order successfully modified")
        return redirect(reverse("admin:core_facture_offreprep_licence_changelist"))


class ChangeDoctorPointsWizard(SessionWizardView):
    form_list = [ChangePointsForm1, ChangePointsForm2]
    template_name = "admin/doctor_change_admin.html"

    @method_decorator(login_required)
    @method_decorator(staff_member_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        context.update({
            'title': 'Gestion des points',
            'app_label': Medecin._meta.app_label,
            'opts': Medecin._meta
        })
        return context

    def get_form(self, step=None, data=None, files=None):
        form = super(ChangeDoctorPointsWizard, self).get_form(step, data, files)

        # Determine the step if not given
        if step is None:
            step = self.steps.current
        if step == '1':
            # Return number of forms for formset requested
            # in previous step.
            userchoice = self.get_cleaned_data_for_step('0')
            medecin = userchoice['medecin']
            cform = ChangePointsForm2(initial={'points': medecin.points}, data=data, medecin=medecin)
            return cform
        return form

    def done(self, form_list, **kwargs):
        for fitem in form_list:
            fitem.save()

        messages.success(self.request, "points successfully modified")
        return redirect(reverse("admin:core_medecin_changelist"))
