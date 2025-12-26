from allauth.account.views import login
from django.conf.urls import url
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import include, path
from django.views.generic.base import TemplateView

from core import autocomplete
from core.admin import CarteProfessionnelleAdmin
from core.views import doctor_views, views, patient_views, staff_views, professional_views
from clinique.views import views as clinique_views, historique_views, virtual_office_views
from core.views.views import ValidationTelplateView
from coupons.admin import GenerateCouponsAdminView

urlpatterns = [
    #url(r'^index/$', views.index, name='index'),
    url(r'^signup/$', views.signup, name='account_signup'),
    url(r'^signup/workspace/$', views.signupWorkspace, name='account_signup_workspace'),
    path('', include('allauth.urls')),
    # Doctor Urls
    url(r'^login/qr/$', views.qrCodeLogin, name='qr-code-login'),
    url(r'^$', login, name='index'),
    url(r'^doctor/dashboard/$', doctor_views.dashboard, name='doctor-dashboard'),
    url(r'^doctor/offers/$', doctor_views.offers, name='doctor-offers'),
    url(r'^doctor/offers/(?P<pk>\d+)$', doctor_views.detailOffer, name='doctor-offer-detail'),
    url(r'^doctor/subscribe/(?P<offer_id>\d+)/(?P<slug>[\w-]+)/$', doctor_views.subscribe, name='doctor-subscribe'),
    url(r'^doctor/order/offer/sponsorised/$', doctor_views.OfferSponsorisedOrderView.as_view(),
        name='doctor-order-offer-sponsorised'),
    url(r'^doctor/order/offer/(?P<offer_id>\d+)/$', doctor_views.orderOffer, name='doctor-order-offer'),
    url(r'^doctor/order/offer/(?P<offer_id>\d+)/(?P<coupon_id>\d+)/$', doctor_views.orderOffer,
        name='doctor-order-offer-with-discount'),
    url(r'^doctor/profile/$', doctor_views.doctorProfile, name='doctor-profile'),
    url(r'^doctor/profile/update$', doctor_views.profile_update, name='doctor-profile-update'),
    url(r'^doctor/profile/update/(?P<medecin_pk>\d+)$', doctor_views.update_profile, name='doctor-profile-update-ajax'),
    url(r'^doctor/profile/certif/delete$', doctor_views.delete_certificat, name='doctor-profile-certif-delete'),


    url(r'^doctor/account/validation/$', TemplateView.as_view(template_name='doctor/account_validation.html'),
        name='doctor-account-validation'),
    url(r'^doctor/identity/verification/$', doctor_views.doctorIdentity, name='doctor-identity'),
    url(r'^doctor/points/history/$', doctor_views.pointsHistory, name='doctor-points-history'),
    url(r'^doctor/cp/upload/$', doctor_views.professionalCardRejected, name='card-rejected'),
    url(r'^doctor/demo/request/(?P<pk>\d+)/$', doctor_views.DemoRequestView.as_view(), name='doctor-demo-request'),
    path('doctor/busy/<int:pk>', doctor_views.BusyView.as_view(), name='doctor-im-busy'),
    path('doctor/annonce/feedback', doctor_views.AnnonceFeedBackView.as_view(), name='doctor-ad-feedback'),
    path('doctor/documentation', doctor_views.docummentation, name='doctor-documentation'),
    #
    path('doctor/care-team/treat', doctor_views.treatCareTeamRequest, name='doctor-care-team-treat'),
    path('doctor/virtual-office', virtual_office_views.virtual_office, name='doctor-virtual-office'),
    path('doctor/carepath/<int:patient_pk>', historique_views.care_path, name='doctor-care-path'),

    # patient url
    url(r'^patient/dashboard/$', patient_views.dashboard, name='patient-dashboard'),
    url(r'^patient/profile/$', patient_views.profile, name='patient-profile'),
    url(r'^patient/profile/update/(?P<patient_pk>\d+)$', patient_views.update_profile, name='patient-profile-update'),
    url(r'^patient/profile/data/remove/(?P<patient_pk>\d+)$', patient_views.remove_profile_data, name='patient-profile-data-remove'),
    url(r'^patient/register/$', patient_views.registerPatient, name='patient-registration'),
    url(r'^patient/carepath/$', historique_views.care_path, name='patient-care-path'),
    url(r'^patient/careteam/$', patient_views.care_team, name='patient-care-team'),

    # professional urls
    url(r'^professional/register/$', views.registerProfessionnelSante, name='professional-registration'),
    url(r'^professional/identity/verification/$', views.professionalIdentity, name='professional-identity'),
    url(r'^professional/account/validation/$', ValidationTelplateView.as_view(template_name='doctor/account_validation.html'),
        name='professional-account-validation'),
    url(r'^professional/dashboard/$', professional_views.dashboard, name='professional-dashboard'),
    url(r'^professional/profile/$', professional_views.profile, name='professional-profile'),
    path('professional/drugs/list', professional_views.drugsList, name='professional-drugs-list'),
    path('professional/drugs/detail', professional_views.drugs_detail, name='professional-drugs-detail'),
    path('professional/drugs/stk/', professional_views.have_in_stock, name='professional-have-in-stock'),

    # Notifications urls
    url(r'^notifications/$', views.notificationsList, name='notifications-list'),
    url(r'^notifications/markAllAsRead$', views.markAllNotificationsAsRead, name='mark-all-notifications-as-read'),
    url(r'^notifications/markAllAsUnread$', views.markAllNotificationsAsUnread,
        name='mark-all-notifications-as-unread'),
    url(r'^notifications/delete', views.deleteNotification, name='delete-notification'),

    # Autocomplete Urls
    url(r'^speciality-autocomplete/$', autocomplete.SpecialityAutocomplete.as_view(), name='speciality-autocomplete'),
    url(r'^qualification-autocomplete/$', autocomplete.QualificationAutocomplete.as_view(),
        name='qualification-autocomplete'),
    url(r'^country-autocomplete/$', autocomplete.CountryAutocomplete.as_view(), name='country-autocomplete'),
    url(r'^user-autocomplete/$', autocomplete.UserAutocomplete.as_view(), name='user-autocomplete'),
    url(r'^carte-autocomplete/$', autocomplete.CarteAutocomplete.as_view(), name='carte-autocomplete'),
    url(r'^city-autocomplete/$', autocomplete.CityAutocomplete.as_view(), name='city-autocomplete'),
    url(r'^ville-autocomplete/$', autocomplete.VilleAutocomplete.as_view(), name='ville-autocomplete'),
    url(r'^region-autocomplete/$', autocomplete.RegionAutocomplete.as_view(), name='region-autocomplete'),
    url(r'^city-search-autocomplete/$', autocomplete.CityGoogleAutocomplete.as_view(), name='city-search-autocomplete'),
    url(r'^contact-autocomplete/$', autocomplete.ContactAutocomplete.as_view(), name='contact-autocomplete'),
    url(r'^operateur-autocomplete/$', autocomplete.OperateurAutocomplete.as_view(),
        name='operateur-autocomplete'),
    url(r'^medecin-autocomplete/$', autocomplete.MedecinAutocomplete.as_view(),
        name='medecin-autocomplete'),
    url(r'^offre-prepaye-autocomplete/$', autocomplete.OffrePrepayeAutocomplete.as_view(),
        name='offre-prepaye-autocomplete'),
    url(r'^offre-partenaire-autocomplete/$', autocomplete.OffrePartenaireAutocomplete.as_view(),
        name='offre-partenaire-autocomplete'),
    url(r'^license-autocomplete/$', autocomplete.LicenseAutocomplete.as_view(), name='license-autocomplete'),
    url(r'^smsmodel-autocomplete/$', autocomplete.SmsModelAutocomplete.as_view(), name='smsmodel-autocomplete'),
    url(r'^smsliste-autocomplete/$', autocomplete.SmsListeAutocomplete.as_view(), name='smsliste-autocomplete'),
    url(r'^emailmodel-autocomplete/$', autocomplete.EmailModelAutocomplete.as_view(), name='emailmodel-autocomplete'),
    url(r'^dci-autocomplete/$', autocomplete.DciAutocomplete.as_view(), name='dci-autocomplete'),
    url(r'^nc-autocomplete/$', autocomplete.NomCommercialAutocomplete.as_view(), name='nc-autocomplete'),
    url(r'^med-autocomplete/$', autocomplete.MedicamentAutocomplete.as_view(), name='med-autocomplete'),
    url(r'^cnas-autocomplete/$', autocomplete.MedicamentCnasAutocomplete.as_view(), name='cnas-autocomplete'),
    url(r'^article-autocomplete/$', autocomplete.ArticleAutocomplete.as_view(), name='article-autocomplete'),
    url(r'^annonce-autocomplete/$', autocomplete.AnnonceAutocomplete.as_view(), name='annonce-autocomplete'),
    url(r'^tag-autocomplete/$', autocomplete.TagAutocomplete.as_view(), name='tag-autocomplete'),
    url(r'^grade-autocomplete', autocomplete.GradeAutocomplete.as_view(), name='grade-autocomplete'),
    url(r'^recently-doctor-autocomplete$', autocomplete.RecentlyDoctorAutocomplete.as_view(),
        name="recently-doctor-autocomplete"),
    url(r'^bank-autocomplete', autocomplete.BankAutocomplete.as_view(), name='bank-autocomplete'),
    url(r'^drugs-autocomplete/$', autocomplete.DrugsModelAutocomplete.as_view(), name='drugs-autocomplete'),
    url(r'^invoice-autocomplete/$', autocomplete.FactureAutocomplete.as_view(), name='invoice-autocomplete'),
    url(r'^patient-autocomplete/$', autocomplete.PatientAutocomplete.as_view(), name='patient-autocomplete'),
    url(r'^partner-autocomplete/$', autocomplete.PartnerAutocomplete.as_view(), name='partner-autocomplete'),
    url(r'^type-exercice-autocomplete/$', autocomplete.TypeExerciceAutocomplete.as_view(),
        name='type-exercice-autocomplete'),

    # Upload Urls
    url(r'^avatar-upload/$', views.avatarUpload, name='avatar-upload'),
    url(r'^cp-upload/$', doctor_views.professionalCardUpload, name='cp-upload'),
    url(r'^sp-cert-upload/$', doctor_views.CertifUpload, name='certificat-upload'),
    url(r'^sp-cert-delete/$', doctor_views.delete_certificat, name='certif-delete'),
    # url(r'^carte-id/$', patient_views.CarteIdCreate.as_view(), name='certificat-upload'),

    # Common Utrls
    url(r'^register/$', views.register, name='registration'),
    url(r'^professional/register/$', views.registerProfessionnelSante, name='professional-registration'),
    url(r'^mobile-app/$', views.etabibMobileApp, name='mobile-app'),
    url(r'^change-password/$', views.ChangePawssordView.as_view(), name='change-password'),
    url(r'^annonce/click/(?P<campagne_id>[-\w]+)/(?P<annonce_id>[-\w]+)/(?P<reseau>\d+)/$', views.annonceClick,
        name='ads-click'),
    url(r'^agree-tos/$', views.agreeTermsOfService, name='agree-tos'),
    url(r'^chat/$', views.rocketchat, name='rocketchat'),
    url(r'^change-template/$', views.changeTemplate, name='change-template'),

    # Staff view Urls
    url(r'^change-card-demand/(?P<pk>\d+)/$', CarteProfessionnelleAdmin.changeCardView,
        name='change-card-demand'),
    url(r'^offer/change/$', staff_views.ChangeOfferWizard.as_view(), name="change-offer-admin"),
    url(r'^points/change/$', staff_views.ChangeDoctorPointsWizard.as_view(), name="change-points-admin"),
    url(r'^generate-coupons/$', staff_member_required(GenerateCouponsAdminView.as_view()),
        name='generate_coupons'),
]
