from django.conf.urls import url

from dicom import views

urlpatterns = [
    url(r'^doctor/dicom/$', views.DicomDatatableView.as_view(), name='doctor-dicom-journal'),
    url(r'^doctor/dicom/create/$', views.PatientCreatDicomView.as_view(),name='doctor-dicom-create'),
]
