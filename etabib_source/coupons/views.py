from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.defaultfilters import upper
from num2words import num2words

from core.utils import applyDiscount
from coupons import settings
from coupons.enums import CouponType
from coupons.models import Coupon


@login_required
def validateCoupon(request):
    if request.is_ajax():
        code = request.POST.get('code', None)
        total = request.POST.get('total', 0)
        target = request.POST.get('target', "1")#see COUPON_TARGETS settings
        if code:
            try:
                coupon = Coupon.objects.get(code=code, target=target)
                if not coupon.is_redeemed and not coupon.expired():
                    if total:
                        total = applyDiscount(total, coupon)
                        total = "%.2f" % total
                        total2words = upper(num2words(total, lang='fr') + " Dinars")
                    return JsonResponse({"id":coupon.id, "value": coupon.value, "total": total,
                                         "total2words": total2words}, status=200)
                return JsonResponse({}, status=401)
            except Coupon.DoesNotExist:
                return JsonResponse({}, status=404)
        return JsonResponse({}, status=400)