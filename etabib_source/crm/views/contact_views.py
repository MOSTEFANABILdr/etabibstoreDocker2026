from ajax_datatable import AjaxDatatableView
from allauth.account.models import EmailAddress
from cities_light.models import City
from datatableview import columns, Datatable
from datatableview.views import DatatableView
from django.contrib import messages
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import DetailView, ListView
from fm.views import AjaxUpdateView
from guardian.mixins import LoginRequiredMixin, PermissionRequiredMixin

from core.decorators import is_operator
from core.enums import Role
from core.models import Contact, OffrePartenaire, OffrePrepaye, Facture, Suivi, DetailAction
from core.templatetags.role_tags import role, has_group
from core.utils import convert_distance
from crm.forms.operator_forms import ContactForm, ArchiveContactForm, ContactFilterForm, SimpleContactForm, \
    PlanStep1Form, PlanStep2Form
from crm.models import Ville
from smsgateway.views import HistoriqueSmsDatatableView, HistoriqueEmailDatatableView


#####################################
# Contact views
#####################################
class ContactDatatable(Datatable):
    adresse = columns.TextColumn(_("Adresse"), sources=None, processor='get_entry_adresse')
    etat = columns.TextColumn(_("Etat"), sources=None, processor='get_entry_etat')
    identifiant = columns.TextColumn(_("Identifiant"), sources=[
        "medecin__user__username", "professionnelsante__user__username", "partenaire__user__username"
    ])
    ville = columns.TextColumn(sources=['ville__name'])
    pays = columns.TextColumn(sources=['pays__name'])
    specialite_libelle = columns.TextColumn(sources="specialite__libelle")
    specialite = columns.TextColumn(sources=None, processor="get_entry_specialite")
    telephone = columns.TextColumn(_("Téléphone"), sources=None, processor="get_entry_telephone")
    email = columns.TextColumn(_("Email"), sources=None, processor="get_entry_email")
    offre = columns.TextColumn(_("Offre"), sources=None, processor="get_entry_offre")
    score = columns.IntegerColumn(_("Score"), sources=["score"])
    actions = columns.TextColumn(_("Actions"), sources=None, processor='get_entry_action')

    class Meta:
        columns = ["id", "identifiant", "etat", "nom", "prenom", "score", "adresse", "specialite", "telephone", "email",
                   "offre", "actions"]
        hidden_columns = ["pays", "ville", "specialite_libelle"]
        search_fields = ["id", "nom", "prenom", "ville", "pays", "specialite__libelle",
                         "medecin__postes__licence__fol_licensce_set__offre__libelle"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-date_creation']
        page_length = 10

    def get_entry_adresse(self, instance, **kwargs):
        return "{}, {}, {}".format(instance.pays.name if instance.pays else "",
                                   instance.ville.name if instance.ville else ""
                                   , instance.adresse)

    def get_entry_etat(self, instance, **kwargs):
        return role(instance, extra_data=True)

    def get_entry_offre(self, instance, **kwargs):
        out = "<ol>"
        if hasattr(instance, "medecin"):
            for tuple in instance.medecin.all_offers:
                offre = tuple[0]
                is_expired = tuple[1]
                if isinstance(offre, OffrePrepaye):
                    out += "<li>%s %s</li>" % (offre.libelle, "(Expired)" if is_expired else "")
        if hasattr(instance, "partenaire"):
            current_offre = instance.partenaire.current_offre()
            if isinstance(current_offre, OffrePartenaire):
                out += "<li>%s</li>" % current_offre.libelle
        out += "</ol>"
        return out

    def get_entry_telephone(self, instance, **kwargs):
        out = "<ul>"
        if instance.fixe:
            out += "<li>%s</li>" % instance.fixe
        if instance.mobile:
            out += "<li>%s</li>" % instance.mobile
        return out

    def get_entry_email(self, instance, **kwargs):
        out = "<ul>"
        for email in instance.get_emails():
            out += "<li>%s</li>" % email
        out += "</ul>"
        return out

    def get_entry_specialite(self, instance, **kwargs):
        if instance.specialite:
            return instance.specialite
        else:
            ""

    def get_entry_action(self, instance, **kwargs):
        request = None
        if 'view' in kwargs:
            request = kwargs.get("view").request
        return render_to_string("partial/datatable-contacts-actions.html",
                                {'contact': instance, "request": request, 'perms': PermWrapper(request.user)})

    def normalize_config(self, config, query_config):
        self.date_joined_from = query_config.get('date_joined_from', None)
        self.date_joined_to = query_config.get('date_joined_to', None)
        self.filter_stats = query_config.get('filter_stats', None)
        return super(ContactDatatable, self).normalize_config(config, query_config)

    def search(self, queryset):
        if self.filter_stats:
            if self.filter_stats == "default_filter":
                queryset = Contact.objects.all()
            elif self.filter_stats == "filter_verified_doctors":
                queryset = Contact.objects.filter(
                    medecin__isnull=False,
                    medecin__carte__checked=True
                )
            elif self.filter_stats == "filter_doctors_without_offer":
                queryset = Contact.objects.filter(
                    medecin__isnull=False, medecin__carte__checked=True, medecin__facture__fol_facture_set__isnull=True
                )
            elif self.filter_stats == "filter_doctors_no_cards":
                queryset = Contact.objects.filter(
                    Q(medecin__isnull=False, medecin__carte__isnull=True) |
                    Q(professionnelsante__isnull=False, professionnelsante__carte__isnull=True)
                )
            elif self.filter_stats == "filter_rejected_cards":
                queryset = Contact.objects.filter(
                    Q(medecin__isnull=False, medecin__carte__rejected=True) |
                    Q(professionnelsante__isnull=False, professionnelsante__carte__rejected=True)
                )
            elif self.filter_stats == "filter_partners":
                queryset = Contact.objects.filter(
                    partenaire__isnull=False
                )
            elif self.filter_stats == "filter_contacts":
                queryset = Contact.objects.filter(
                    medecin__isnull=True, partenaire__isnull=True, professionnelsante__isnull=True
                )
            elif self.filter_stats == "filter_archived":
                queryset = Contact.archived_objects.all()
        if self.date_joined_from:
            queryset = queryset.filter(
                Q(medecin__user__date_joined__gte=self.date_joined_from) |
                Q(partenaire__user__date_joined__gte=self.date_joined_from) |
                Q(professionnelsante__user__date_joined__gte=self.date_joined_from)
            )
        if self.date_joined_to:
            queryset = queryset.filter(
                Q(medecin__user__date_joined__gte=self.date_joined_to) |
                Q(partenaire__user__date_joined__gte=self.date_joined_to) |
                Q(professionnelsante__user__date_joined__gte=self.date_joined_to)
            )
        return super(ContactDatatable, self).search(queryset)

    def count_objects(self, base_objects, filtered_objects):
        if isinstance(base_objects, QuerySet):
            num_total = base_objects.count()
        else:
            num_total = len(base_objects)
        if isinstance(filtered_objects, QuerySet):
            num_filtered = filtered_objects.count()
        else:
            num_filtered = len(filtered_objects)
        return num_total, num_filtered


class ContactDatatableView(DatatableView):
    template_name = "communication/contact-list.html"
    model = Contact
    datatable_class = ContactDatatable

    def get_context_data(self, **kwargs):
        context = super(ContactDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Contact List")
        context["oper_list_contact"] = True
        context["default_filter_counts"] = self.get_queryset().count()
        context["doctors_counts"] = Contact.objects.filter(
            medecin__isnull=False,
            medecin__carte__checked=True
        ).distinct().count()
        context["doctors_witout_offer_count"] = Contact.objects.filter(
            medecin__isnull=False, medecin__carte__checked=True, medecin__facture__fol_facture_set__isnull=True
        ).distinct().count()
        context["doctors_no_cards_counts"] = Contact.objects.filter(
            Q(medecin__isnull=False, medecin__carte__isnull=True) |
            Q(professionnelsante__isnull=False, professionnelsante__carte__isnull=True)
        ).distinct().count()
        context["doctors_cards_rejected_counts"] = Contact.objects.filter(
            Q(medecin__isnull=False, medecin__carte__rejected=True) |
            Q(professionnelsante__isnull=False, professionnelsante__carte__rejected=True)
        ).distinct().count()
        context["partners_counts"] = Contact.objects.filter(partenaire__isnull=False).count()
        context["contacts_counts"] = Contact.objects.filter(
            medecin__isnull=True, partenaire__isnull=True, professionnelsante__isnull=True
        ).distinct().count()
        context["archived_counts"] = Contact.archived_objects.filter().count()
        return context

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.request = request
        return super(ContactDatatableView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Contact.objects.all()
        return qs.distinct()


@login_required
@is_operator
def addContact(request):
    """
    Add contact
    :param request:
    :return:
    """
    title = _("Add Contact")
    if request.method == 'POST':
        if has_group(request.user, Role.DELEGUE_COMMERCIAL.value):
            form = SimpleContactForm(request.POST, request.FILES)
        else:
            form = ContactForm(request.POST, request.FILES)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.cree_par = request.user.operateur
            contact.save()
            form.save_m2m()
            messages.success(request, _('Contact was added'))
            if request.user.has_perm('core.crm_can_view_simplified_contact_list'):
                return redirect("operator-list-contact-simplified")
            return redirect("operator-list-contact")
    else:
        if has_group(request.user, Role.DELEGUE_COMMERCIAL.value):
            form = SimpleContactForm(initial={'pays': 62})
        else:
            form = ContactForm()
    context = {"form": form, "title": title, "oper_list_contact": True}
    return render(request, "communication/add-contact.html", context)


@login_required
@is_operator
def editContact(request, pk):
    """
    Edit an existing contact
    :param request:
    :param pk: id of the contact
    :return:
    """
    title = _("Edit Contact")
    edit = True
    contact = get_object_or_404(Contact, pk=pk)
    if request.method == 'POST':
        form = ContactForm(request.POST, request.FILES, instance=contact)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.save()
            form.save_m2m()
            messages.success(request, _('Les informations de contact ont été mises à jour avec succès '))

    form = ContactForm(instance=contact)
    context = {
        "form": form,
        "title": title,
        "edit": edit,
        "contact": contact
    }
    return render(request, "communication/add-contact.html", context)


class ContactDetailView(DetailView):
    model = Contact
    template_name = "communication/contact-detail.html"

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super(ContactDetailView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ContactDetailView, self).get_context_data(**kwargs)

        sms_hist_view = HistoriqueSmsDatatableView()
        sms_hist_view.contact_id = self.get_object().id
        datatable = sms_hist_view.get_datatable(url=reverse("sms-history", args=[self.get_object().id, ]))
        context['datatable_sms'] = datatable

        if hasattr(self.get_object(), "medecin"):
            context['orders'] = self.get_object().medecin.facture_set.all()
        if hasattr(self.get_object(), "partenaire"):
            context['orders'] = Facture.objects.filter(partenaire=self.get_object().partenaire)

        email_hist_view = HistoriqueEmailDatatableView()
        email_hist_view.contact = self.get_object()
        datatable = email_hist_view.get_datatable(url=reverse("email-history", args=[self.get_object().id, ]))
        context['datatable_email'] = datatable

        return context


class ArchiveContactView(SuccessMessageMixin, AjaxUpdateView):
    form_class = ArchiveContactForm
    model = Contact
    success_message = _("Contact archivé avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=Contact.all_objects.all()):
        return super(ArchiveContactView, self).get_object(queryset=queryset)

    def form_valid(self, form):
        if self.object.archive:
            self.object.archive = False
            self.success_message = _("Contact Déarchivé!")
        else:
            self.object.archive = True
            self.success_message = _("Contact Archivé!")
        return super(ArchiveContactView, self).form_valid(form)


class ContactListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Contact
    template_name = "communication/contact-list-simplified.html"
    permission_required = 'core.crm_can_view_simplified_contact_list'
    return_403 = True

    def get_context_data(self, **kwargs):
        context = super(ContactListView, self).get_context_data(**kwargs)
        context['oper_list_contact_simplified'] = True
        context['filter_form'] = ContactFilterForm()
        initial2 = {
            "rayon": 10
        }
        context.update({
            "step1": PlanStep1Form(), "step2": PlanStep2Form(initial=initial2)
        })
        return context


class ContactAjaxDatatableView(LoginRequiredMixin, PermissionRequiredMixin, AjaxDatatableView):
    model = Contact
    title = 'Contacts'
    initial_order = []
    show_column_filters = False
    search_values_separator = '+'
    permission_required = 'core.crm_can_view_simplified_contact_list'
    return_403 = True

    column_defs = [
        {'name': 'pk', 'title': 'N°', 'visible': True, },
        {'name': '_status', 'title': _("Etat"), 'searchable': False, 'orderable': False, },
        {'name': 'nom', "searchable": True, 'visible': False, },
        {'name': 'prenom', "searchable": True, 'visible': False, },
        {'name': 'nom_prenom', 'title': _("Nom"), "searchable": False, 'visible': True, },
        {'name': '_adresse', 'title': _("Adresse"), "searchable": False, 'visible': True, },
        {'name': 'adresse', 'visible': False, "searchable": True},
        {'name': 'departement', 'visible': False, "searchable": True},
        {'name': 'commune', 'visible': False, "searchable": True},
        {'name': 'specialite', 'foreign_field': 'specialite__libelle', 'title': _('Spécialité'), 'visible': True, },
        {'name': '_telephone', 'title': _("Téléphone"), 'searchable': False, 'orderable': False, },
        {'name': '_distance', 'title': _("Distance"), 'searchable': False, 'orderable': False, },
        {'name': 'fixe', 'searchable': True, 'visible': False, },
        {'name': 'mobile', 'searchable': True, 'visible': False, },
        {'name': 'mobile_1', 'searchable': True, 'visible': False, },
        {'name': 'mobile_2', 'searchable': True, 'visible': False, },
        {'name': 'actions', 'title': 'Actions', 'searchable': False, 'orderable': False, },
    ]

    def customize_row(self, row, obj):
        tel = ""
        address = ""
        if obj.fixe:
            tel += obj.fixe + "<br>"
        if obj.mobile:
            tel += obj.mobile + "<br>"
        if obj.mobile_1:
            tel += obj.mobile_1 + "<br>"
        if obj.mobile_2:
            tel += obj.mobile_2
        if obj.adresse:
            address += obj.adresse
        if obj.departement:
            address += obj.departement  + "<br>"
        if obj.commune:
            address += obj.commune  + "<br>"
        row['_status'] = role(obj, extra_data=True)
        row['_telephone'] = tel
        row['_distance'] = convert_distance(obj.distance) if hasattr(obj, "distance") else ""
        row['_adresse'] = address
        row['nom_prenom'] = "%s %s" % (obj.nom or "", obj.prenom or "")
        row['actions'] = render_to_string(
            "partials/datatable-contact-simpl-actions.html",
            {'contact': obj, 'perms': PermWrapper(self.request.user), "is_client": "Client" in row['_status']}
        )
        return

    def get_initial_queryset(self, request=None):
        if not getattr(request, 'REQUEST', None):
            request.REQUEST = request.GET if request.method == 'GET' else request.POST

        queryset = Contact.objects.filter().exclude(partenaire__isnull=False).exclude(Q(Q(nom__exact='') | Q(
            nom__isnull=True) & (Q(prenom__exact='') | Q(prenom__isnull=True)))).order_by("-id")

        if 'specialite_id' in request.REQUEST:
            specialite_id = request.REQUEST.get('specialite_id')
            if specialite_id and specialite_id != "null":
                queryset = queryset.filter(specialite__id=specialite_id)

        distance = 50
        if 'distance' in request.REQUEST:
            try:
                distance = int(request.REQUEST.get('distance', 50))
            except Exception as ex:
                distance = 50

        if 'commune_id' in request.REQUEST:
            commune_id = request.REQUEST.get('commune_id')
            if commune_id and commune_id != "null":
                ville = Ville.objects.filter(id=commune_id).first()
                if ville:
                    degrees = distance / 111.325
                    ref_location = Point(float(ville.latitude), float(ville.longitude), srid=4326)
                    queryset = queryset.filter(
                        geo_coords__distance_lte=(ref_location, degrees)
                    ).annotate(
                        distance=Distance("geo_coords", ref_location)
                    ).order_by('distance')

        return queryset.prefetch_related("prospect")


@login_required
def verify_email(request):
    if request.is_ajax():
        email = request.GET.get("email", None)
        if email:
            if not User.objects.filter(Q(email=email) | Q(username=email)).exists() and not EmailAddress.objects.filter(
                    email=email).exists():
                return JsonResponse(True, status=200, safe=False)
        return JsonResponse(False, status=200, safe=False)
    return JsonResponse(False, status=400, safe=False)

def _filter_contacts(kwargs):
    specialite_q = kwargs.get("specialite_q", None)
    max_prospect = kwargs.get("max_prospect", None)
    inclure_visiteur = kwargs.get("inclure_visiteur", None)
    inclure_unknown = kwargs.get("inclure_unknown", None)
    commune_depart = kwargs.get("commune_depart", None)
    rayon = kwargs.get("rayon", None)

    try:
        rayon = int(rayon)
    except Exception as ex:
        rayon = 10

    try:
        max_prospect = int(max_prospect)
    except Exception as ex:
        max_prospect = 10

    inclure_unknown = False if inclure_unknown == 'false'  else True if inclure_unknown == 'true' else None
    inclure_visiteur = False if inclure_visiteur == 'false'  else True if inclure_visiteur == 'true' else None

    qs = Contact.objects.filter(medecin__postes__isnull=True, partenaire__isnull=True, prospect__isnull=True)
    if specialite_q:
        if inclure_unknown:
            qs = qs.filter(Q(specialite__id=specialite_q) | Q(specialite__isnull=True))
        else:
            qs = qs.filter(Q(specialite__id=specialite_q))
    else:
        if not inclure_unknown:
            qs = qs.filter(Q(specialite__isnull=False))

    if not inclure_visiteur:
        qs = qs.filter(professionnelsante__isnull=True)

    if commune_depart and rayon:
        ville = Ville.objects.filter(id=commune_depart).first()
        if ville:
            degrees = rayon / 111.325
            ref_location = Point(float(ville.latitude), float(ville.longitude), srid=4326)
            qs = qs.filter(
                geo_coords__distance_lte=(ref_location, degrees)
            ).annotate(
                distance=Distance("geo_coords", ref_location)
            ).order_by('distance')
    return (qs, max_prospect)

@login_required
def filter_contacts(request):
    if request.is_ajax():
        qs, max_prospect = _filter_contacts(request.POST)

        all_count =  qs.count()
        if qs.query.is_sliced:
            cm = 0
            cv = 0
            c = 0
            for contact in qs:
                if hasattr(contact, "medecin"):
                    cm += 1
                elif hasattr(contact, "professionnelsante"):
                    cv += 1
                else:
                    c += 1

            out = {
                "all_count": all_count,
                "doctor_count": cm,
                "visitor_count": cv,
                "contacts_count": c,
            }
        else:
            out = {
                "all_count": all_count,
                "doctor_count": qs.filter(medecin__isnull=False).count(),
                "visitor_count": qs.filter(professionnelsante__isnull=False).count(),
                "contacts_count": qs.filter(medecin__isnull=True, professionnelsante__isnull=True).count(),
            }

        paginator = Paginator(qs, max_prospect)
        out["nb_list"] = paginator.num_pages

        return JsonResponse(out, status=200, safe=False)
    return JsonResponse({}, status=400, safe=False)

#################################
# List suivi views
#################################
class ListeSuiviDatatable(Datatable):
    contact_nom = columns.TextColumn(source=['contact__nom'])
    contact = columns.TextColumn(_("Contact"), processor="get_entry_contact")
    contact_prenom = columns.TextColumn(source=['contact__prenom'])
    date_last_update = columns.TextColumn(_("Prochaine date de contact"), source=None,
                                          processor='get_entry_date_last_update')
    cree_par = columns.IntegerColumn(_("Ajouté par"), sources=["cree_par"])
    action = columns.TextColumn(_("Actions"), source=None, processor='get_entry_action')

    class Meta:
        columns = ["contact", "cree_par", "date_last_update"]
        hidden_columns = ["contact_nom", "contact_prenom"]
        search_fields = ["id", 'contact__nom', 'contact__prenom']
        structure_template = "partial/datatable-bootstrap-structure.html"
        page_length = 10
        ordering = ['-id']

    def get_entry_action(self, instance, **kwargs):
        details = DetailAction.objects.filter(action__contact=instance.contact, action__type="2")
        if details.exists():
            last_detail = details.latest("id")
            return "<a class='btn btn-etabib' href='%s?scrl=detail_%s'>%s</a>" % (
                reverse("action-detail", args=[last_detail.action.id]),
                last_detail.id,
                _("Voir détail")
            )
        else:
            return ""

    def get_entry_contact(self, instance, **kwargs):
        if instance.contact:
            return "<a href='{}'>{}</a>".format(
                reverse('operator-detail-contact', args=(instance.contact.id,)), instance.contact
            )
        return ""

    def get_entry_date_last_update(self, instance, **kwargs):
        date_last_update = None
        out = ""
        details = DetailAction.objects.filter(action__contact=instance.contact, action__type="2")
        if details.exists():
            last_detail = details.latest("id")
            if hasattr(last_detail, 'prochainerencontre'):
                date_last_update = last_detail.prochainerencontre.date_rencontre
            else:
                date_last_update = last_detail.date_creation.date()

        if date_last_update:
            out = "<p class='%s'>%s</p>"
            if date_last_update > timezone.now().date():
                out = out % ("green", date_last_update.strftime("%Y-%m-%d"))
            else:
                out = out % ("red", date_last_update.strftime("%Y-%m-%d"))
        return out


class ListeSuiviDatatableView(DatatableView):
    template_name = "communication/list-suivi.html"
    model = Suivi
    datatable_class = ListeSuiviDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ListeSuiviDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Listes de suivi")
        context['oper_sidebar_list_suivi'] = True
        return context
