from django.conf.urls import url
from django.urls import path

from core import autocomplete
from directory.views import directory_views, signup_views

urlpatterns = [
    path(r'directory', directory_views.directory_index, name='directory'),
    path(r'directory/signup', signup_views.signup_directory, name='signup-directory'),
    path(r'directory/signup/step/two', signup_views.signup_step_two, name='signup-directory-stp-two'),
    path(r'signup/<str:pk>', signup_views.signup_doctor_link_directory, name='doctor-pages-signup'),
    path(r'signup/', signup_views.signup_doctor_directory, name='doctor-signup'),
    url(r'^medecin-autocomplete-gl-specialite/$', autocomplete.ContactGoogleSpecialiteAutocomplete.as_view(),
        name='medecin-autocomplete-gl-sp'),
]
