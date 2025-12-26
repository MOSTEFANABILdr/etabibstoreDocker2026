from django import template

from basket.cart import Cart
from basket.settings import CART_TEMPLATE_TAG_NAME

register = template.Library()


@register.simple_tag(takes_context=True, name=CART_TEMPLATE_TAG_NAME)
def get_cart(context, session_key=None, cart_class=Cart):
    """
    Make the cart object available in template.

    Sample usage::

        {% load carton_tags %}
        {% get_cart as cart %}
        {% for product in cart.products %}
            {{ product }}
        {% endfor %}
    """
    request = context['request']
    return cart_class(request.session, session_key=session_key)


@register.simple_tag(takes_context=True)
def cartCounts(session):
    cart = Cart(session, session_key=None)
    length = cart.unique_count
    return length if length > 0 else ""


@register.simple_tag(name='wasaddedtocart')
def wasAddedToCart(module, session, poste):
    cart = Cart(session, session_key=None)
    for cartItem in cart.items:
        if cartItem.poste == poste and cartItem.product.pk == module.pk:
            return True
    return False
