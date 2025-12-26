"""
ASGI entrypoint. Configures Django and then runs the application
defined in the ASGI_APPLICATION setting.
"""

import os
from urllib.parse import parse_qs

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etabibWebsite.settings')
django_asgi_app = get_asgi_application()

from django.contrib.auth.models import AnonymousUser
from core import routing
from rest_framework.authtoken.models import Token
from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from channels.routing import ProtocolTypeRouter, URLRouter


@database_sync_to_async
def get_user(token_key):
    # If you are using normal token based authentication
    try:
        token = Token.objects.get(key=token_key)
        return token.user
    except Token.DoesNotExist:
        return AnonymousUser()


class TokenAuthMiddleware(BaseMiddleware):
    """
    Token authorization middleware for channels
    """

    def __init__(self, inner):
        super().__init__(inner)

    async def __call__(self, scope, receive, send):
        query_string = scope['query_string']
        if query_string:
            parsed_query = parse_qs(query_string)
            token_key = parsed_query[b'token'][0].decode()
            token_name = 'token'
            if token_name == 'token':
                scope['user'] = await get_user(token_name)
        return await super().__call__(scope, receive, send)


def TokenAuthMiddlewareStack(inner):
    return TokenAuthMiddleware(AuthMiddlewareStack(inner))


application = ProtocolTypeRouter({
    # Empty for now (http->django views is added by default)
    "http": django_asgi_app,
    'websocket': TokenAuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})
