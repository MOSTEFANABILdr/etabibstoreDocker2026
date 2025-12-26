'''
Created on 01 jav 2019

@author: ZAHI
'''

from django import template
from django.template.loader import render_to_string
from django.utils.html import format_html

from api.views.ads_views import getAd
from core.enums import AdsDestination, AdTypeHelper
from core.models import AnnonceFeed
from core.templatetags.ads_tags import feeds

register = template.Library()


@register.simple_tag
def loadBreakingNews(request, user):
    destination = AdsDestination.WEB
    annonces = getAd(request, destination, AdTypeHelper.FEED, multiple=True)
    context = {
        "annonces": annonces,
        "user": user
    }
    return render_to_string('partial/breaking-news.html', context)

@register.simple_tag
def get_annonces_web(request):
    destination = AdsDestination.WEB
    annonces = getAd(request, destination, AdTypeHelper.FEED, multiple=True)
    return annonces


@register.simple_tag
def loadBreakingNewsStaticFiles():
    return format_html("<!-- Jquery ticker CSS ============================================ -->"
                       "<link href='/static/css/jquery-ticker/breaking-news-ticker.min.css?v=1.2' rel=\"stylesheet\" type=\"text/css\" />"
                       "<script src='/static/js/jquery-ticker/breaking-news-ticker.min.js' type=\"text/javascript\"></script>")
