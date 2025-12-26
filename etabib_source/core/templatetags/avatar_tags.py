'''
Created on 01 jav 2019

@author: ZAHI
'''

import avinit
from django import template
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

register = template.Library()


@register.simple_tag
def avatar(user, **kwargs):
    if isinstance(user, User):
        if hasattr(user, 'avatar'):
            url = user.avatar.image.url
        else:
            """
                The commented code is used to generate avatars by
                calling an API.
            """
            # if hasattr(user, 'avatar'):
            #     avatar = user.avatar
            #     url = avatar.image.url
            #     alt = user.first_name
            #     tooltip = user.get_full_name()
            # else:
            #     try:
            #         avatar = Avatar()
            #         img_url = "https://ui-avatars.com/api/?name={}+{}&&size=200".format(user.first_name, user.last_name)
            #         name = slugify("{} {}".format(user.first_name, user.last_name), allow_unicode=True)
            #         content = requests.get(img_url).content
            #         fp = BytesIO()
            #         fp.write(content)
            #         avatar.user = user
            #         avatar.image.save(name, files.File(fp))
            #         avatar.save()
            #         url = avatar.image.url
            #     except Exception  as e:
            #         print(e)
            #         url = ""
            #         tooltip = ""
            #     alt = _("Default Avatar")
            """
                The below code is used to generate avatar by
                using avinit library
            """
            if user.first_name or user.last_name:
                url = avinit.get_avatar_data_url('{} {}'.format(user.first_name, user.last_name))
            else:
                url = avinit.get_avatar_data_url('{}'.format(user.username))

        tooltip = user.get_full_name()
        alt = user.first_name

    else:
        url = ""
        alt = ""
        tooltip = ""

    kwargs.update({'alt': alt})
    context = {
        'user': user,
        'url': url,
        'tooltip': tooltip,
        'kwargs': kwargs,
    }
    return render_to_string('avatar/avatar_tag.html', context)


@register.filter
def has_avatar(user):
    if not isinstance(user, User):
        return False
    else:
        return True


@register.simple_tag
def avatar_url(user):
    if isinstance(user, User):
        if hasattr(user, 'avatar'):
            domain = Site.objects.get_current().domain
            url = 'http://%s%s' % (domain, user.avatar.image.url)
        else:
            url = avinit.get_avatar_data_url('{} {}'.format(user.first_name, user.last_name))
    else:
        url = "#"
    return url
