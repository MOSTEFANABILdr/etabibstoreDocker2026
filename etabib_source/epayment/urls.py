from django.conf.urls import url
from django.urls import path

from epayment import views

urlpatterns = [
    url(r'recharge/', views.epaymentPortal, name='epayment-recharge'),
    path('method/<str:user_hash>/<str:offer_hash>/<str:coupon_hash>', views.epaymentMethod, name='epayment-method-coupon'),
    path('method/<str:user_hash>/<str:offer_hash>', views.epaymentMethod, name='epayment-method'),
    url(r'^virement/create/$', views.VirementCreateView.as_view(), name="virement-ajouter"),
    url(r'preview/(?P<ordre_uuid>[\w-]+)/$', views.epaymentPreview, name='epayment-preview'),
]