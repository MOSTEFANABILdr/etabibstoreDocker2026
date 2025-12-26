from django.conf.urls import url

from filesharing.views import patient_views, doctor_views

urlpatterns = [
    url(r'^doctor/file/list$', patient_views.listFiles, name='doctor-files-list'),
    url(r'^doctor/file/fetch$', patient_views.fetchFiles, name='doctor-files-fetch'),
    url(r'^file/share/(?P<file_id>[\w-]+)/(?P<type>\d+)/$', doctor_views.ShareFileView.as_view(),
        name='file-share'),
    url(r'^doctor/file/rename/(?P<file_id>[\w-]+)/$', doctor_views.RenameFileView.as_view(),
        name='file-rename'),

    url(r'^patient/file/list$', patient_views.listFiles, name='patient-files-list'),
    url(r'^patient/file/fetch$', patient_views.fetchFiles, name='patient-files-fetch'),
    url(r'^patient/file/get/(?P<file_id>[\w-]+)/$', patient_views.getFile, name='patient-files-get'),
    url(r'^patient/file/delete/(?P<file_id>[\w-]+)/$', patient_views.deleteFile, name='patient-files-delete'),

    url(r'^file-upload/$', patient_views.uploadFile, name='file-upload'),
]
