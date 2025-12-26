from decimal import Decimal

from django.conf import settings

from core.models import Poste
from . import module_loading
from . import settings as carton_settings


class CartItem(object):
    """
    A cart item, with the associated product, its quantity and its price.
    """
    def __init__(self, product, quantity, price, poste):
        self.product = product
        self.quantity = int(quantity)
        self.price = Decimal(str(price))
        self.poste = poste

    def __repr__(self):
        return u'CartItem Object (%s)' % self.product

    def to_dict(self):
        return {
            'product_pk': self.product.pk,
            'quantity': self.quantity,
            'price': str(self.price),
            'poste_pk': self.poste.pk,
        }

    @property
    def subtotal(self):
        """
        Subtotal for the cart item.
        """
        return self.price * self.quantity


class Cart(object):

    """
    A cart that lives in the session.
    """
    def __init__(self, session, session_key=None):
        self._items_dict = {}
        self.session = session
        self.session_key = session_key or carton_settings.CART_SESSION_KEY
            # If a cart representation was previously stored in session, then we
        if self.session_key in self.session:
            # rebuild the cart object from that serialized representation.
            cart_representation = self.session[self.session_key]
            for key in cart_representation.keys():
                pd_pk = key.split("-")[0]
                products_queryset = self.get_queryset().filter(pk=pd_pk)
                if products_queryset:
                    product = products_queryset.first()
                    item = cart_representation[key]
                    poste = Poste.objects.get(pk=item['poste_pk'])
                    self._items_dict[(product.pk, poste.pk)] = CartItem(
                        product, item['quantity'], Decimal(item['price']),
                        poste
                    )

    def __contains__(self, product):
        """
        Checks if the given product is in the cart.
        """
        return product in self.products

    def get_product_model(self):
        return module_loading.get_product_model()

    def filter_products(self, queryset):
        """
        Applies lookup parameters defined in settings.
        """
        lookup_parameters = getattr(settings, 'CART_PRODUCT_LOOKUP', None)
        if lookup_parameters:
            queryset = queryset.filter(**lookup_parameters)
        return queryset

    def get_queryset(self):
        product_model = self.get_product_model()
        queryset = product_model._default_manager.all()
        queryset = self.filter_products(queryset)
        return queryset

    def update_session(self):
        """
        Serializes the cart data, saves it to session and marks session as modified.
        """
        self.session[self.session_key] = self.cart_serializable
        self.session.modified = True

    def add(self, product, poste,  price=None, quantity=1):
        """
        Adds or creates products in cart. For an existing product,
        the quantity is increased and the price is ignored.
        """
        quantity = int(quantity)
        if quantity < 1:
            raise ValueError('Quantity must be at least 1 when adding to cart')
        exists = False
        for item in self.items:
            if item.product == product and item.poste == poste:
                exists = True

        if exists:
            self._items_dict[(product.pk, poste.pk)].quantity += quantity
        else:
            if price == None:
                raise ValueError('Missing price when adding to cart')
            self._items_dict[(product.pk, poste.pk)] = CartItem(product, quantity, price, poste)
        self.update_session()

    def remove(self, product, poste):
        """
        Removes the product.
        """
        if product in self.products:
            del self._items_dict[(product.pk, poste.pk)]
            self.update_session()

    def remove_single(self, product, poste):
        """
        Removes a single product by decreasing the quantity.
        """
        if product in self.products:
            if self._items_dict[(product.pk, poste.pk)].quantity <= 1:
                # There's only 1 product left so we drop it
                del self._items_dict[(product.pk, poste.pk)]
            else:
                self._items_dict[(product.pk, poste.pk)].quantity -= 1
            self.update_session()

    def clear(self):
        """
        Removes all items.
        """
        self._items_dict = {}
        self.update_session()

    def set_quantity(self, product, quantity, poste):
        """
        Sets the product's quantity.
        """
        quantity = int(quantity)
        if quantity < 0:
            raise ValueError('Quantity must be positive when updating cart')
        if product in self.products:
            self._items_dict[(product.pk, poste.pk)].quantity = quantity
            if self._items_dict[(product.pk, poste.pk)].quantity < 1:
                del self._items_dict[(product.pk, poste.pk)]
            self.update_session()

    @property
    def items(self):
        """
        The list of cart items.
        """
        return self._items_dict.values()

    @property
    def cart_serializable(self):
        """
        The serializable representation of the cart.
        For instance:
        {
            '1': {'product_pk': 1, 'quantity': 2, price: '9.99'},
            '2': {'product_pk': 2, 'quantity': 3, price: '29.99'},
        }
        Note how the product pk servers as the dictionary key.
        """
        cart_representation = {}
        for item in self.items:
            # JSON serialization: object attribute should be a string
            product_id = str(item.product.pk)
            poste_id = str(item.poste.pk)
            cart_representation["%s-%s" % (product_id, poste_id)] = item.to_dict()
        return cart_representation


    @property
    def items_serializable(self):
        """
        The list of items formatted for serialization.
        """
        return self.cart_serializable.items()

    @property
    def count(self):
        """
        The number of items in cart, that's the sum of quantities.
        """
        return sum([item.quantity for item in self.items])

    @property
    def unique_count(self):
        """
        The number of unique items in cart, regardless of the quantity.
        """
        return len(self._items_dict)

    @property
    def is_empty(self):
        return self.unique_count == 0

    @property
    def products(self):
        """
        The list of associated products.
        """
        return [item.product for item in self.items]

    @property
    def total(self):
        """
        The total value of all items in the cart.
        """
        return sum([item.subtotal for item in self.items])
