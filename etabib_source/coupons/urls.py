from django.urls import path

from coupons import views

urlpatterns = [
    path('validate', views.validateCoupon, name='validate-coupon'),
]
