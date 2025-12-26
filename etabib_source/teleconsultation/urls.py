from django.conf.urls import url
from django.urls import path

from core import autocomplete
from teleconsultation.views import doctor_views, patient_views

urlpatterns = [
    url(r'^doctor/teleconsultation/$', doctor_views.TeleconsultationJournalDatatableView.as_view(),
        name='doctor-teleconsultation-journal'),
    url(r'^doctor/teleconsultation/bill/$', doctor_views.billTeleconsultation,
        name='doctor-teleconsultation-bill'),
    url(r'^doctor/teleconsultation/claim/(?P<pk>\d+)/(?P<tdemand_pk>\d+)/$', doctor_views.ClaimَUpdateView.as_view(),
        name='doctor-teleconsultation-update-claim'),
    path('doctor/teleconsultation/<uuid:unique_id>', doctor_views.teleconsultation, name='doctor-teleconsultation'),
    url(r'^doctor/contact/$', doctor_views.contacts, name="doctor-contact"),
    url(r'^doctor/contact/create/$', doctor_views.patient_create, name='doctor-contact-create'),
    url(r'^contact/qrcode/(?P<pk>\d+)/$', doctor_views.patient_create_qr, name='contact-qrcode'),

    url(r'^patient/teleconsultation/$', patient_views.doctorsList, name='patient-teleconsultation'),
    path('patient/teleconsultation/<uuid:unique_id>', doctor_views.teleconsultation, name='patient-teleconsultation'),
    url(r'^patient/teleconsultation/journal/$', patient_views.TeleconsultationJournalDatatableView.as_view(),
        name='patient-teleconsultation-journal'),
    url(r'^patient/teleconsultation/claim/(?P<tdemand_pk>\d+)/$', patient_views.ClaimَCreateView.as_view(),
        name='patient-teleconsultation-create-claim'),
    url(r'^patient/teleconsultation/claim/(?P<pk>\d+)/(?P<tdemand_pk>\d+)/$', patient_views.ClaimَUpdateView.as_view(),
        name='patient-teleconsultation-update-claim'),
    url(r'^patient/teleconsultation/coupon/$', patient_views.UseCouponView.as_view(),
        name='patient-teleconsultation-coupon'),
    url(r'^patient/teleconsultation/profile/(?P<doctor_id>\d+)/$', patient_views.viewDoctorProfile,
        name='patient-view-doctor-profile'),
    path('patient/care-team/add', patient_views.addToCareTeam, name='patient-care-team-add'),

    url(r'^teleconsultation/feedback', patient_views.teleconsultationFeedback, name="teleconsultation-feedback"),
    url(r'^teleconsultation/sessions/(?P<demand_pk>\d+)/$', doctor_views.teleconsultationSessions,
        name="teleconsultation-sessions"),
    url(r'^patient/carteID/$', doctor_views.create_carte_id, name='post-card-id'),
]
