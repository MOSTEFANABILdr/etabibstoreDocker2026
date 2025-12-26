from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404

from basket.cart import Cart
from core.enums import WebsocketCommand
from core.models import Module, Poste, Version, Installation
from django.utils.translation import gettext as _


@login_required
def add(request):
    if request.is_ajax():
        pk = request.POST.get('pk', None)
        cart = Cart(request.session)
        product = Module.objects.get(id=pk)
        cart.add(product, price=product.consomation)
        return JsonResponse({'status': "success"}, status=200)
    return JsonResponse({'error': "no content"}, status=405)


@login_required
def remove(request):
    if request.is_ajax():
        pk_module = request.POST.get('pk_module', None)
        pk_poste = request.POST.get('pk_poste', None)
        cart = Cart(request.session)
        product = Module.objects.get(id=pk_module)
        poste = Poste.objects.get(id=pk_poste)
        cart.remove(product, poste)
        # send notification through channels
        channel_layer = get_channel_layer()
        room_group_name = 'chat_%s' % request.user.pk
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'notification_message',
                'data': {
                    'command': WebsocketCommand.FETCH_CART_COUNTS.value,
                    'count': cart.unique_count
                }
            }
        )
        return JsonResponse({'status': "success"}, status=200)
    return JsonResponse({'error': "no content"}, status=405)


@login_required
def show(request):
    return render(request, 'shopping/show-cart.html', using=request.template_version)


@login_required
def validateShopping(request):
    if request.is_ajax():
        cart = Cart(request.session)
        for item in cart.items:
            version = get_object_or_404(Version, module=item.product, lastversion=True)
            installation = Installation()
            installation.version = version
            installation.poste = item.poste
            installation.save()

        cart.clear()
        # send notification through channels
        channel_layer = get_channel_layer()
        room_group_name = 'chat_%s' % request.user.pk
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'notification_message',
                'data': {
                    'command': WebsocketCommand.FETCH_CART_COUNTS.value,
                    'count': cart.unique_count
                }
            }
        )

        return JsonResponse(
            {
                'status': "success",
                "success_message": _("L'achat des applications est validé")
            }, status=200)
    return JsonResponse({'error': "no content"}, status=405)
