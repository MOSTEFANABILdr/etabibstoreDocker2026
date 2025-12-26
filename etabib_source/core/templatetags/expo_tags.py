from django import template
from django.contrib.auth.models import User
from django.core.serializers import serialize

from core.enums import Role

register = template.Library()


@register.simple_tag
def get_badge_color(user):
    if isinstance(user, User):
        if user.groups.filter(name=Role.DOCTOR.value).exists():
            return "#FF851B"#ORANGE
        elif user.groups.filter(name=Role.PHARMACIST.value).exists():
            return "#FF4136"#RED
        elif user.groups.filter(name=Role.STUDENT.value).exists():
            return "#85144b"#MAROON
        elif user.groups.filter(name=Role.ADMINISTRATION.value).exists():
            return "#B10DC9"  # PURPLE
        elif user.groups.filter(name=Role.MINISTRY.value).exists():
            return "#111111"  # BLACK
        elif user.groups.filter(name=Role.PSYCHOLOGIST.value).exists():
            return "#AAAAAA"#GRAY
        elif user.groups.filter(name=Role.MEDICAL_PURCHASING_MANAGER.value).exists():
            return "#001f3f"  #NAVY
        elif user.groups.filter(name=Role.MEDICAL_COMPANY_MANAGER.value).exists():
            return "#0074D9"  # BLUE
        elif user.groups.filter(name=Role.DENTIST.value).exists():
            return "#7FDBFF"  # AQUA
        elif user.groups.filter(name=Role.RESEARCHER.value).exists():
            return "#3D9970"  # OLIVE
        elif user.groups.filter(name=Role.PARAMEDICAL.value).exists():
            return "#2ECC40"  # GREEN
        elif user.groups.filter(name=Role.AUXILIARY.value).exists():
            return "#01FF70"  # LIME
