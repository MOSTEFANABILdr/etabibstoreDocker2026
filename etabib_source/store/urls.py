from django.conf.urls import url

from store import views

urlpatterns = [
    url(r'^store/$', views.eTabibStore, name='etabib-store'),
    url(r'^store/v1$', views.eTabibV1Store, name='etabib-store-v1'),
    url(r'^store/v2$', views.eTabibV2Store, name='etabib-store-v2'),
    url(r'^workspace/$', views.etabibWorkspace, name='etabib-workspace'),
    url(r'^store/my/(?P<poste_id>\d+)/$', views.eTabibStoreMyApps, name='etabib-store-my-apps-by-postes'),
    url(r'^store/my/$', views.eTabibStoreMyApps, name='etabib-store-my-apps'),
    url(r'^store/tag/(?P<tag>[\w-]+)/$', views.eTabibStoreTagApps, name='etabib-store-tag-apps'),
    url(r'^store/item/(?P<pk>\d+)/(?P<slug>[\w-]+)/$', views.eTabibStoreItemDetail,
        name='etabib-store-item'),
    url(r'^store/item/addComment$', views.addComment, name='etabib-store-item-add-comment'),
    url(r'^store/item/removeComment/$', views.removeComment, name='etabib-store-item-remove-comment'),
    url(r'^store/item/addRating/$', views.addAppRating, name='etabib-store-item-add-rating'),
    url(r'^store/item/install/$', views.installApplication, name='etabib-store-item-installation'),
    url(r'^store/item/status/$', views.getAppStatus, name='etabib-store-item-get-app-status'),
    url(r'^store/search/$', views.searchApp, name='etabib-store-search'),
]
