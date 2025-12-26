import tempfile

import weasyprint
from ajax_datatable import AjaxDatatableView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from el_pagination.decorators import page_template
from guardian.decorators import permission_required

from clinique.models import OrdonnanceMedic, Ordonnance
from core.decorators import has_access
from core.enums import EtabibService
from core.forms.professionnal_forms import DciAtcForm
from drugs.models import DciAtc, NomCommercial, Medicament
from etabibWebsite.settings import STATIC_ROOT


@login_required
@page_template('prescription_detail.html')
@permission_required("core.can_veiw_e_prescription", return_403=True)
@has_access(EtabibService.E_PRESCRIPTION)
def prescription(request, template="prescription.html", extra_context=None):
    context = {}
    dci = None
    dci_id = None
    if request.is_ajax():
        if request.method == 'POST':
            # First call
            dci_id = request.POST.get('dci_id', None)
        if request.method == 'GET':
            # pagination call
            dci_id = request.GET.get('dci_id', None)
    if dci_id:
        dci = DciAtc.objects.get(id=dci_id)
        ncs = NomCommercial.objects.filter(medicament__dci_atc=dci).distinct()
        if ncs.exists():
            context['nom_commerciaux'] = ncs
            context['nc_count'] = ncs.count()
        else:
            context['nom_commerciaux'] = NomCommercial.objects.none()
            context['nc_count'] = 0
            # TODO: search by CodeAtc
        # passing dci_id to pagination url
        context['extra_args'] = "&dci_id=%s" % dci_id

    # TODO one ordonnance per doctor ???
    ordonnance = Ordonnance.objects.filter(operateur=request.user.medecin)
    # IF no ordonnance is associated to this oprt & dmd then create one
    if not ordonnance:
        ordonnance = Ordonnance(operateur=request.user.medecin)
        ordonnance.save()
    else:
        ordonnance = ordonnance[0]

    context['ordonnance_pk'] = ordonnance.pk
    context['form'] = DciAtcForm(initial={'dci': dci})
    context['sidebar_presc'] = True
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context, using=request.template_version)


class OrdonnanceADatatable(AjaxDatatableView, PermissionRequiredMixin, LoginRequiredMixin):
    permission_required = ''
    return_403 = True
    model = OrdonnanceMedic
    title = 'Ordonnance Medicament'
    search_values_separator = '+'
    length_menu = [[10, 20, 50, 100, -1], [10, 20, 50, 100, 'all']]

    column_defs = [
        {'name': 'pk', 'title': 'id', 'visible': False, },
        {'name': 'dci', 'title': 'DCI', 'foreign_field': 'medicament__dci_atc__designation_fr'},
        {'name': 'nom_commercial', 'title': 'Nom Commercial',
         'foreign_field': 'medicament__nom_commercial__nom_fr', },
        {'name': 'forme', 'title': 'Forme',
         'foreign_field': 'medicament__forme_homogene__designation', },
        {'name': 'posologie', 'title': 'Posologie', 'width': 180},
        {'name': 'cond', 'title': 'Cond', 'foreign_field': 'medicament__cond', },
        {'name': 'dosage', 'title': 'Dosage', 'foreign_field': 'medicament__dosage'},
        {'name': 'actions', 'title': _('Action'), 'searchable': False, },
    ]

    def customize_row(self, row, obj):
        row['posologie'] = """
            <textarea class="form-control ordomedic-row" oninput="update_poso(this)" data-id='%s'>%s</textarea>
        """ % (obj.pk, obj.posologie)

        row['actions'] = """
            <a class="btn btn-danger" title="%s" onclick="removeFromOrdonnance(%s)">
                <i class="fa fa-times"></i>
            </a>
        """ % (_("Supprimer"), obj.pk)

        return

    def get_initial_queryset(self, request=None):
        if 'ordonnance_pk' in request.POST:
            # Show ordonnance
            ordo_id = request.POST.get('ordonnance_pk')
            ordo = Ordonnance.objects.get(pk=ordo_id, operateur=request.user.medecin)
            return OrdonnanceMedic.objects.filter(ordonance=ordo).order_by('-pk')

        else:
            return OrdonnanceMedic.objects.none()


@login_required
def load_menu_detail(request):
    if request.is_ajax():
        context = {}
        if 'medicId' in request.POST and 'forme' in request.POST:
            context = {'pk': request.POST.get('medicId'), 'forme': request.POST.get('forme')}
            template = "menu_medic_comp_nb.html"
        else:
            template = "menu_medic_details.html"
            context['details'] = Medicament.objects.filter(pk__in=request.POST.getlist('details[]', None)).distinct()

        return render(request, template, context)

    return JsonResponse({'status': "Unprocessable Entity"}, status=422)


@login_required
@permission_required("core.can_veiw_e_prescription", return_403=True)
@has_access(EtabibService.E_PRESCRIPTION)
def add_medic_ordo(request):
    if request.is_ajax():
        if 'ordonnance_pk' in request.POST and 'medic_pk' in request.POST:
            ordonance = get_object_or_404(Ordonnance, pk=request.POST.get('ordonnance_pk'))
            medicament = get_object_or_404(Medicament, pk=request.POST.get('medic_pk'))
            ordonnancemedic = OrdonnanceMedic(ordonance=ordonance, medicament=medicament)
            ordonnancemedic.posologie = request.POST.get('medic_ps', None)
            ordonnancemedic.save()
            return JsonResponse({}, status=200)

    return JsonResponse({'status': "Unprocessable Entity"}, status=422)


@login_required
@permission_required("core.can_veiw_e_prescription", return_403=True)
@has_access(EtabibService.E_PRESCRIPTION)
def remove_medic_ordo(request):
    if request.is_ajax():
        get_object_or_404(OrdonnanceMedic, id=request.POST.get('id', None)).delete()
        return JsonResponse({}, status=200)
    else:
        return JsonResponse({'status': "Unprocessable Entity"}, status=422)


@login_required
@permission_required("core.can_veiw_e_prescription", return_403=True)
@has_access(EtabibService.E_PRESCRIPTION)
def ordonnance_as_pdf(request, ordo_id=None):
    """Generate pdf."""
    # Model data
    patient_name = request.GET.get('patient', None)
    patient_age = request.GET.get('age', None)
    ordo = Ordonnance.objects.get(pk=ordo_id)
    html_string = render_to_string('ordonnance_template.html',
                                   {'ordonnancemedic': ordo.ordonnancemedic_set.all(),
                                    'ordo': ordo,
                                    'medecin': request.user.medecin,
                                    'patient_name': patient_name,
                                    'patient_age': patient_age,
                                    'format': 'A5'})
    pg = weasyprint.CSS(
        string=(
            """
            @page {
                size: a5;
                margin: 1cm;
                @frame footer {
                    -pdf-frame-content: footerContent;
                    bottom: 0cm;
                    margin-left: 9cm;
                    margin-right: 9cm;
                    height: 1cm;
                }
            }
            """
        )
    )

    stylesheets = [
        weasyprint.CSS(STATIC_ROOT + '/style.css'),
        weasyprint.CSS(STATIC_ROOT + '/css/bootstrap.min.css'),
        pg
    ]
    html = weasyprint.HTML(
        string=html_string, base_url=request.build_absolute_uri('/')
    ).render(stylesheets=stylesheets)

    result = html.write_pdf()

    # Creating http response
    response = HttpResponse(content_type='application/pdf;')
    response['Content-Disposition'] = 'inline; filename=ordonnance.pdf'
    response['Content-Transfer-Encoding'] = 'binary'
    with tempfile.NamedTemporaryFile(delete=True) as output:
        output.write(result)
        output.flush()
        output = open(output.name, 'rb')
        response.write(output.read())
    return response


@login_required
@permission_required("core.can_veiw_e_prescription", return_403=True)
@has_access(EtabibService.E_PRESCRIPTION)
def ordonnance_update(request):
    if request.is_ajax():
        if 'id' in request.POST and 'poso' in request.POST:
            medic_ordo = OrdonnanceMedic.objects.get(pk=request.POST.get('id'))
            medic_ordo.posologie = request.POST.get('poso')
            medic_ordo.save()
            return JsonResponse({}, status=200)

    return JsonResponse({'status': "Unprocessable Entity"}, status=422)
