from django.conf.urls import url
from django.urls import path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from api.views import views, demande_rdv_views, econgre_views, hl7_views, doctor_lsc_views, utils_views, patient_views
from api.views import teleconsultation_views
from api.views import ads_views
from api.views import nomenclature_views
from api.views import drugs_views
from etabibWebsite import settings
from etabibWebsite.settings import Environment

schema_view = get_schema_view(
    openapi.Info(
        title="eTabib Store API",
        default_version='v1',
        description="etabibstore api description",
    ),
    url='https://etabibstore.com/api/' if settings.ENVIRONMENT == Environment.PROD else "http://127.0.0.1:8000/api/",
    # important bit
    public=True,
    permission_classes=(permissions.IsAdminUser,),
)
urlpatterns = [
    url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    url(r'^generateid/(?P<mac>[\w-]+)/$', views.GenerateUniqueIdentifierView.as_view()),
    url(r'^activate/$', views.ActivateLicenceView.as_view()),
    url(r'^activation/$', views.ActivateLicenceView.as_view()),
    url(r'^updater/last/$', views.LastUpdaterView.as_view()),
    url(r'^bddscript/last/$', views.GetBddScriptView.as_view()),
    url(r'^poste/setlastconnectiondate/$', views.SetLastConnectionDateView.as_view()),
    url(r'^poste/checksid/$', views.CheckSIDView.as_view()),
    url(r'^poste/certificates/$', views.GenerateCertificatesView.as_view()),
    url(r'^poste/checkForUpdates/(?P<version>.+)/$', views.CheckForUpdatesView.as_view()),
    url(r'^poste/etabib/update/confirm', views.ConfirmEtabibInstallationView.as_view()),
    url(r'^poste/plugin/install/confirm', views.ConfirmPluginInstallationView.as_view()),
    url(r'^poste/updater/install/confirm', views.ConfirmUpdaterInstallationView.as_view()),
    url(r'^poste/plugin/uninstall/confirm', views.ConfirmPluginUninstallationView.as_view()),
    url(r'^poste/plugin/update/confirm', views.ConfirmPluginUpdateView.as_view()),
    url(r'^poste/migration/check', views.CheckForMigrationView.as_view()),
    url(r'^poste/migration/do', views.DoMigrationView.as_view()),
    url(r'^poste/offre/', doctor_lsc_views.DoctorLscView.as_view()),
    path('doctor/register', views.RegisterFromInstallerView.as_view()),

    # Drug interaction WS
    url(r'^dci/interaction/check', views.DrugInteractionView.as_view()),
    # Drug change log
    url(r'^drug/changelog', drugs_views.ChangeLogView.as_view()),
    url(r'^drug/changedrugs', drugs_views.ChangeDrugsView.as_view()),
    # Find Nomenclature WS
    url(r'^nomenclature/find', nomenclature_views.FindNomenclatureView.as_view()),
    url(r'^loincnabm/find', nomenclature_views.FindLoincNabmAPIView.as_view()),
    path("motif/find", nomenclature_views.FindMotifView.as_view({"get": "list"})),
    # Collect Statistics WS
    url(r'^stats/collect', views.CollectStatisticsView.as_view()),
    # Eula
    url(r'^eula/check', views.CheckEulaView.as_view()),
    url(r'^eula/accept/(?P<id>\d+)/$', views.AcceptEulaView.as_view()),
    #
    path('dictionary/', views.DictionaryViewSet.as_view()),
    #
    path('feed', views.IbnHamzaFeedView.as_view()),
    # rest API
    url(r'^token-auth/', views.MacAuthToken.as_view()),
    url(r'^intervention/create/$', views.DemandeIntervetionCreate.as_view()),
    url(r'^intervention/image/upload/$', views.DiImageUploadView.as_view()),
    url(r'^user/$', views.CustomUserDetailsView.as_view()),
    ## Ads Urls ##
    url(r'^annonce/impression/(?P<campagne_id>[-\w]+)/(?P<annonce_id>[-\w]+)/(?P<user_id>\d+)/(?P<reseau>\d+)/$',
        ads_views.AdImpressionView.as_view(),
        name="ad-impression"),
    url(r'^annonce/impression/(?P<wvideo_id>\d+)/(?P<user_id>\d+)/(?P<duree>\d+)/$',
        ads_views.AdCongreImpressionView.as_view(),
        name="ad-impression-congre"),
    url(r'annonce/list/$', ads_views.GetAdsList.as_view(), name="ads-list"),
    url(r'annonce/get/$', ads_views.GetAdView.as_view(), name="ads-get"),
    url(r'annonce/download/confirmation/$', ads_views.AdDownloadConfirationView.as_view(),
        name="ad-download-confirmation"),
    url(r'annonce/upload/statistics/$', ads_views.UploadCampaignsStatisticsView.as_view(), name="ad-upload-statistics"),
    # Teleconsultation
    url(r'^patient/login/$', teleconsultation_views.OnlyPatientLoginView.as_view()),
    url(r'^teleconsultation/doctors/list/$', teleconsultation_views.DoctorsListView.as_view()),
    url(r'^teleconsultation/speakers/stats/$', teleconsultation_views.SpeakerStatsView.as_view()),
    url(r'^patient/solde/(?P<pk>\d+)/$', teleconsultation_views.SoldeView.as_view()),
    url(r'^doctor/login/$', teleconsultation_views.OnlyDoctorLoginView.as_view()),
    url(r'^teleconsultation/busy/doctor/$', teleconsultation_views.BusyDoctorView.as_view()),

    # Rendez vous
    url(r'^teleconsultation/rdv/list/$', demande_rdv_views.RdvListView.as_view()),
    url(r'^teleconsultation/rdvdoctor/list/$', demande_rdv_views.RdvDoctorNotificationListView.as_view()),
    url(r'^teleconsultation/demandes/add/$', demande_rdv_views.AddDemandeRdv.as_view(), name="add-demande-rdv"),
    url(r'^teleconsultation/demandes/can/$', demande_rdv_views.CancelDemandeRdv.as_view(), name="can_demande-rdv"),
    url(r'^teleconsultation/getEconsultationDomain/$', views.GetEconsultationDomain().as_view(),
        name="econsultation-domain"),

    # Econgre
    url(r'^econgres/$', econgre_views.ListEcongre.as_view(), name="list-econgre"),
    url(r'^econgres/(?P<congre_id>\d+)/webinars$', econgre_views.ListWebinar.as_view(), name="list-econgre-webinar"),

    #utils
    url(r'^country/(?P<pk>\d+)$', utils_views.ContrytDetail.as_view(), name="country-detail"),
    url(r'^city/(?P<pk>\d+)$', utils_views.CitytDetail.as_view(), name="city-detail"),
    url(r'^speciality/(?P<pk>\d+)$', utils_views.SpecialityDetail.as_view(), name="speciality-detail"),
    url(r'^qualification/(?P<pk>\d+)$', utils_views.QualificationDetail.as_view(), name="qualification-detail"),
    url(r'^bank/(?P<pk>\d+)$', utils_views.BankDetail.as_view(), name="bank-detail"),

    # eTabibclinic
    url(r'^patient/(?P<hash_pk>[\w]+)$', patient_views.PatientIdView.as_view()),

]
