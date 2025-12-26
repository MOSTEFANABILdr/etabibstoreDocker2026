from django.conf.urls import url
from django.urls import path

from ads.views import partner_views
from core import autocomplete
from expo import views

urlpatterns = [
    path('', views.expos, name='etabib-expo'),
    path('signup', views.signup, name='etabib-expo-signup'),
    url(r'^stand-autocomplet/$', autocomplete.StandsModelAutocomplete.as_view(), name='stand-autocomplete'),
    path('stand/detail/<int:pk>', views.stand_detail, name='expo-stand-detail'),
    path('campany/detail/<int:pk>', views.campany_detail, name='expo-campany-detail'),
    path('product/preorder/<int:article_pk>', views.PrecommandeArticleCreateView.as_view(),
         name='expo-product-preorder'),
    path('badge', views.badge, name='expo-badge'),
    path('badge/<str:token>', views.badge, name='expo-badge-verification'),
    path('catalogue/list/<int:partner_id>', partner_views.catalogueList, name='expo-catalogue-list'),
    url(r'^stand/visio/(?P<stand_id>\d+)$', views.standVisio, name='expo-stand-visio'),
    url(r'^stand/visio/status$', views.checkStandVisio, name='expo-stand-visio-check'),
    url(r'^stand/visio$', views.standVisio, name='expo-stand-visio-enter'),
    path('exposants/', views.ExposantDatatableView.as_view(), name='expo-list-partenaire'),
    path('firmes/', views.FirmeDatatableView.as_view(), name='expo-list-marque'),
]