from ajax_datatable import AjaxDatatableView
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import ListView
from guardian.mixins import LoginRequiredMixin, PermissionRequiredMixin
from post_office import mail

from core.decorators import is_operator
from core.enums import Role
from core.models import DetailAction, CarteProfessionnelle, Medecin, Action
from crm.forms.operator_forms import CommandeUploadForm
from crm.models import Commande, CommandeImage, BordereauVersement


@login_required
@is_operator
def upload_commande_image(request):
    if request.method == 'POST':
        form = CommandeUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            ci = form.save()
            ci.user = request.user
            ci.save()
            return JsonResponse({'file_id': ci.id}, status=200)
        else:
            return JsonResponse({'error': form.errors}, status=400)


@login_required
@is_operator
def create_untreated_commande(request):
    if request.method == 'POST':
        email = request.POST.get("email", None)
        nom = request.POST.get("nom", None)
        prenom = request.POST.get("prenom", None)
        telephone = request.POST.get("telephone", None)
        offre = request.POST.get("offre", None)
        quantite = request.POST.get("quantite", None)
        paiement = request.POST.get("paiement", None)
        commande_image_id = request.POST.get("commande_image", None)
        versement_initial = request.POST.get("versement_initial", None)
        totalHt = request.POST.get("totalHt", None)
        action_id = request.POST.get("action_id", None)

        action = get_object_or_404(Action, id=action_id)
        cimage = get_object_or_404(CommandeImage, id=commande_image_id)
        contact = action.contact

        # create user
        with transaction.atomic():
            if hasattr(contact, "medecin"):
                user = contact.medecin.user
                user.first_name = nom
                user.last_name = prenom
                user.save()

                medecin = contact.medecin

                cp = CarteProfessionnelle()
                cp.checked = True
                cp.save()

                medecin.carte = cp

                medecin.save()

                contact.email = email
                contact.mobile = telephone
                contact.save()
            elif hasattr(contact, "professionnelsante"):
                user = contact.professionnelsante.user
                user.first_name = nom
                user.last_name = prenom

                contact.email = email
                contact.mobile = telephone

                medecin = Medecin()
                medecin.user = contact.professionnelsante.user
                medecin.contact = contact
                medecin.carte = contact.professionnelsante.carte
                medecin.user.groups.set([Group.objects.get(name=Role.DOCTOR.value)])

                contact.professionnelsante.user = None
                contact.professionnelsante.carte = None

                cp = CarteProfessionnelle()
                cp.checked = True
                cp.save()

                medecin.carte = cp

                medecin.save()
                contact.professionnelsante.delete()

                contact.save()

            else:
                user = User()

                group = Group.objects.get(name=Role.DOCTOR.value)

                user.first_name = nom
                user.last_name = prenom
                password = User.objects.make_random_password()
                contact.nom = nom
                contact.prenom = prenom
                contact.mdp_genere = password
                contact.email = email
                contact.mobile = telephone
                user.set_password(password)
                user.username = email
                user.email = email
                user.save()
                user.groups.add(group)

                mailaddr = EmailAddress()
                mailaddr.user = user
                mailaddr.primary = True
                mailaddr.verified = True
                mailaddr.email = email
                mailaddr.save()

                contact.save()

                # Create doctor
                medecin = Medecin()
                medecin.user = user
                medecin.contact = contact
                # medecin carte
                cp = CarteProfessionnelle()
                cp.checked = True
                cp.save()

                medecin.carte = cp

                medecin.save()

                mail.send(
                    user.email,
                    settings.DEFAULT_FROM_EMAIL,
                    template='registration',
                    context={
                        'username': user.email,
                        'password': password,
                        'login_link': "{}://{}".format(request.scheme, request.get_host())
                    },
                )

            detail = DetailAction()
            detail.cree_par = request.user.operateur
            detail.type = "D"  # Déplacement Visite
            detail.action = action
            detail.save()
            extra_args = "?scrl=detail_%s" % detail.id

            commande = Commande()
            commande.quantite = quantite
            commande.user = user
            commande.cree_par = request.user
            commande.methode_paiement = paiement
            commande.offre = offre
            commande.image = cimage
            commande.detail_action = detail
            commande.versement_initial = versement_initial
            commande.totalHt = totalHt
            commande.save()


        return JsonResponse(
            {
                "redirection_url": reverse('action-detail', kwargs={"pk": action_id}) + extra_args
            }, status=200
        )
    else:
        return JsonResponse({}, status=400)


class UntreatedCommandeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Commande
    template_name = "operator/command-list.html"
    permission_required = 'core.crm_can_view_untreated_command_list'
    return_403 = True

    def get_context_data(self, **kwargs):
        context = super(UntreatedCommandeListView, self).get_context_data(**kwargs)
        context['com_sidebar_list_untreated_order'] = True
        return context


class UntreatedCommandeAjaxDatatableView(LoginRequiredMixin, PermissionRequiredMixin, AjaxDatatableView):
    model = Commande
    title = 'Commandes'
    initial_order = [["pk", "desc"]]
    show_column_filters = False
    search_values_separator = '+'
    permission_required = 'core.crm_can_view_untreated_command_list'
    return_403 = True

    def initialize(self, request):
        self.is_delegue = request.user.groups.filter(name=Role.DELEGUE_COMMERCIAL.value).exists()
        return super(UntreatedCommandeAjaxDatatableView, self).initialize(request)

    def get_column_defs(self, request):
        column_defs = [
            {'name': 'pk', 'title': 'N°', 'visible': True, },
            {'name': 'contact', 'title': _("Contact"), "searchable": False, 'visible': True, },
            {'name': 'operateur', 'title': _("Opérateur"), "searchable": False, 'visible': True, },
            {'name': 'contact_nom', 'foreign_field': 'user__first_name', "searchable": True, 'visible': False, },
            {'name': 'contact_prenom', 'foreign_field': 'user__last_name', "searchable": True, 'visible': False, },
            {'name': 'operateur_nom', 'foreign_field': 'cree_par__first_name', "searchable": True, 'visible': False, },
            {'name': 'operateur_prenom', 'foreign_field': 'cree_par__last_name', "searchable": True,
             'visible': False, },
            {'name': 'offre', 'visible': True, "searchable": True},
            {'name': 'quantite', 'visible': True, "searchable": True},
            {'name': 'methode_paiement', 'visible': True, "searchable": True},
            {'name': 'date_creation', 'visible': True, "searchable": True},
            {'name': 'totalHt', 'title': _("Total HT"), 'visible': True, "searchable": True},
            {'name': 'versement_initial', 'visible': True, "searchable": True},
            {'name': 'image', 'title': _("Image"), "searchable": False, 'visible': True, },
            {'name': 'actions', 'title': 'Actions', 'searchable': False, 'orderable': False, },
        ]
        if self.is_delegue:
            column_defs.pop(2)
        return column_defs

    def customize_row(self, row, obj):
        obj = Commande.objects.get(id=obj.id)
        row['contact'] = "<a target='_blanc' href='/operator/contact/%s'> %s</a>" % (
            obj.user.medecin.contact.id,
            obj.user.medecin.contact.full_name or ""
        )
        if not self.is_delegue:
            row['operateur'] = obj.cree_par.get_full_name()
        row['image'] = "<a target='_blanc' href='%s'>Voir Image</a>" % (obj.image.image.url)
        row['actions'] = render_to_string(
            "partials/datatable-untr-commandes-actions.html",
            {'commande': obj, 'perms': PermWrapper(self.request.user), "is_delegue": self.is_delegue}
        )
        return

    def get_initial_queryset(self, request=None):
        queryset = super(UntreatedCommandeAjaxDatatableView, self).get_initial_queryset(request=request)
        if self.is_delegue:
            queryset = queryset.filter(cree_par=request.user)
        return queryset


@login_required
@is_operator
def generate_bordereau(request):
    if request.method == 'POST':
        commande_ids = request.POST.getlist("commands[]", None)
        if len(commande_ids):
            commands = Commande.objects.filter(id__in=commande_ids)
            total = 0
            with transaction.atomic():
                for command in commands:
                    total += command.versement_initial

                bv = BordereauVersement()
                bv.cree_par = request.user
                bv.total = total
                bv.save()

                for command in commands:
                    command.bordereau = bv
                    command.save()
                messages.success(request, f"Bourdereau de versement N° {bv.id} a été généré avec succès.")

            return JsonResponse(
                {
                }, status=200
            )
    return JsonResponse({}, status=400)


class BordereauListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = BordereauVersement
    template_name = "operator/bordereau-list.html"
    permission_required = 'core.crm_can_view_bordereau_list'
    return_403 = True

    def get_context_data(self, **kwargs):
        context = super(BordereauListView, self).get_context_data(**kwargs)
        context['com_sidebar_list_bordereau'] = True
        return context


class BordereauAjaxDatatableView(LoginRequiredMixin, PermissionRequiredMixin, AjaxDatatableView):
    model = BordereauVersement
    title = 'Bordereaux'
    initial_order = [["pk", "desc"]]
    show_column_filters = False
    search_values_separator = '+'
    permission_required = 'core.crm_can_view_bordereau_list'
    return_403 = True

    def get_column_defs(self, request):
        column_defs = [
            {'name': 'pk', 'title': 'N°', 'visible': True, },
            {'name': 'operateur', 'title': _("Opérateur"), "searchable": False, 'visible': True, },
            {'name': 'total', 'title': _("Total") },
            AjaxDatatableView.render_row_tools_column_def(),
        ]
        return column_defs

    def render_row_details(self, pk, request=None):
        obj = BordereauVersement.objects.get(pk=pk)
        return render_to_string('partials/bordereau_row_tools.html', {
            'obj': obj,
        })

    def customize_row(self, row, obj):
        obj = BordereauVersement.objects.get(id=obj.id)
        row['operateur'] = obj.cree_par.get_full_name()
        return

    def get_initial_queryset(self, request=None):
        queryset = super(BordereauAjaxDatatableView, self).get_initial_queryset(request=request)
        queryset = queryset.filter(cree_par=request.user)
        return queryset
