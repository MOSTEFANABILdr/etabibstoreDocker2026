from django.conf.urls import url

from appointements.views import doctor_views, patient_views, partner_views, professional_views

urlpatterns = [
    # doctor urls
    url(r'^demands/doctor$', doctor_views.DemandeRendezVousDatatableView.as_view(), name='doctor-appointments'),
    url(r'^create/$', doctor_views.CreateAppointmentView.as_view(), name='doctor-create-appointments'),
    url(r'^agenda/$', doctor_views.AppointmentEvents, name='appointments-agenda'),
    url(r'^agenda/fetch/$', doctor_views.fetchAppointmentsEvents, name='fetch-appoinments-events'),
    url(r'^process/(?P<pk>\d+)$', doctor_views.RendezVousProcessView.as_view(), name='process-appointment-request'),
    url(r'^recently-patient-autocomplete$', doctor_views.RecentlyPatientAutocomplete.as_view(),
        name="recently-patient-autocomplete"),
    url(r'^demands/doctor/qr/$', doctor_views.qrCodeReader, name='doctor-qrcode-reader'),
    url(r'^demands/doctor/patient/$', doctor_views.create_dmd_rdv, name='doctor-dmd-rdv'),
    url(r'^demands/doctor/patient/cancel/$', doctor_views.doctor_dmd_rdv_can, name='doctor-dmd-rdv-can'),
    # patient urls
    url(r'^demands/patient$', patient_views.DemandeRendezVousDatatableView.as_view(), name='patient-appointments'),
    url(r'^agenda/patient', patient_views.agenda, name='patient-appointments-agenda'),
    # partner urls
    url(r'^demands/partner$', partner_views.DemandeRendezVousDatatableView.as_view(), name='partner-appointments'),
    url(r'^agenda/partner$', partner_views.AppointmentEvents, name='partner-appointments-agenda'),
    # professional urls
    url(r'^agenda/professional$', professional_views.AppointmentEvents, name='professional-appointments-agenda'),
]
