from django.conf.urls import url
from django.urls import path

from clinique.views import prescription_views, views, documents_views, historique_views, virtual_office_views

urlpatterns = [
    path('prescription', prescription_views.prescription, name='prescription'),
    path('ordonnance', prescription_views.OrdonnanceADatatable.as_view(), name='ordonnance'),
    path('menu-detail', prescription_views.load_menu_detail, name='ordonnance-menu-detail'),
    path('ordonnance-add', prescription_views.add_medic_ordo, name='ordonnance-add'),
    path('ordonnance-remove', prescription_views.remove_medic_ordo, name='ordonnance-remove'),
    path('ordonnance-pdf/<int:ordo_id>', prescription_views.ordonnance_as_pdf, name='ordonnance-pdf'),
    path('ordonnance-update/', prescription_views.ordonnance_update, name='ordonnance-update'),

    # document
    path('document/create/<int:patient_pk>', documents_views.DocumentCreateView.as_view(), name='document-create'),
    path('document/update/<int:pk>', documents_views.DocumentUpdateView.as_view(), name='document-update'),
    path('document/delete/<int:pk>', documents_views.DocumentDeleteView.as_view(), name='document-delete'),

    # consultation
    path('consultation/create/<int:patient_pk>', views.ConsultationCreateView.as_view(), name="consultation-create"),
    path('consultation/update/<int:pk>', views.ConsultationUpdateView.as_view(), name="consultation-update"),

    # Historique
    path('historique/filter/<int:patient_pk>', historique_views.filter_historique, name="historique-filter"),

    # clinique virtuelle
    path('upload-vcimage/', virtual_office_views.upload_vcimage, name='upload-vcimage'),
    path('remove_vcimage/', virtual_office_views.remove_vcimage, name='remove-vcimage'),
    path('update_virtual_office/', virtual_office_views.virtual_office_update, name='update-virtual-office'),
    path('virtual_offices/', virtual_office_views.virtual_offices_list, name='list-virtual-offices'),
    path('virtual_offices/<int:voffice_id>', virtual_office_views.virtual_office_detail, name='virtual-office-detail'),
    path('doctor/profile/<int:contact_id>', virtual_office_views.virtual_office_doctor_profile, name='doctor-profile-detail'),
    path('virtual_offices/tarifs/<int:voffice_id>', virtual_office_views.virtual_office_tarif, name='virtual-office-tarifs'),

    url(r'^v-secretary/(?P<clinique_id>\d+)$', virtual_office_views.virtual_secretary, name='v-secretary'),
    path('v-secretary/status', virtual_office_views.v_secretary_status, name='v-secretary-status'),
    url(r'^v-secretary/visio', virtual_office_views.v_secretary_visio, name='v-secretary-visio'),

    url(r'^virtual_offices/rendez-vous/(?P<medecin_id>\d+)$', virtual_office_views.RendezVousCreateView.as_view(),
        name='virtual-office-rdv'),

]