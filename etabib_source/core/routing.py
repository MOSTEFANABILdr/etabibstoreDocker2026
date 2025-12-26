from django.conf.urls import url

from core import consumers

websocket_urlpatterns = [
    url(r'^ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
