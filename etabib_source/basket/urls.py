from django.conf.urls import url

from basket import views

urlpatterns = [
    # Basket Urls
    url(r'^add/$', views.add, name='shopping-cart-add'),
    url(r'^remove/$', views.remove, name='shopping-cart-remove'),
    url(r'^show/$', views.show, name='shopping-cart-show'),
    url(r'^validate/$', views.validateShopping, name='shopping-cart-validate'),
]
