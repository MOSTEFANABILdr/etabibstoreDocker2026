'''
Created on 30 déc. 2018

@author: ZAHI
'''
from django import template
from django.utils.html import format_html

from api.views.ads_views import getAd
from core.enums import AdsDestination, AdTypeHelper
from etabibWebsite import settings

register = template.Library()


@register.simple_tag
def ad360x200(request, dest=None):
    print("ad360x200")
    destination = AdsDestination.WEB
    if dest:
        destination = AdsDestination(dest)
    annonce = getAd(request, destination, AdTypeHelper.DISPLAY, settings.ADS_IMAGE_SIZE_CHOICES[2][0])
    return annonce

@register.simple_tag
def feeds(request, dest=None):
    destination = AdsDestination.WEB
    if dest:
        destination = AdsDestination(dest)
    annonce = getAd(request, destination, AdTypeHelper.FEED, multiple=True)
    return annonce

@register.simple_tag
def ad728x360(request, dest=None):
    print("ad728x360")
    destination = AdsDestination.WEB
    if dest:
        destination = AdsDestination(dest)
    annonce = getAd(request, destination, AdTypeHelper.DISPLAY, settings.ADS_IMAGE_SIZE_CHOICES[4][0])
    return annonce


@register.simple_tag
def ad1600x840(request, dest=None):
    destination = AdsDestination.WEB
    if dest:
        destination = AdsDestination(dest)
    annonce = getAd(request, destination, AdTypeHelper.DISPLAY, settings.ADS_IMAGE_SIZE_CHOICES[5][0])
    return annonce


@register.simple_tag
def randomAdDisplay(request, dest=None):
    destination = AdsDestination.WEB
    if dest:
        destination = AdsDestination(dest)
    annonce = getAd(request, destination, AdTypeHelper.DISPLAY, settings.ADS_IMAGE_SIZE_CHOICES[0][0])
    return annonce


@register.simple_tag
def adVideo(request, dest=None):
    destination = AdsDestination.WEB
    if dest:
        destination = AdsDestination(dest)
    annonce = getAd(request, destination, AdTypeHelper.VIDEO, settings.ADS_IMAGE_SIZE_CHOICES[0][0])
    return annonce


@register.simple_tag
def loadCarouselAdsStaticFiles():
    return format_html(
        "<!-- owl.carousel CSS============================================ -->"
        "<link rel = \"stylesheet\" href = '/static/css/carousel/owl.carousel.css'>"
        "<link rel = \"stylesheet\"  href = '/static/css/carousel/owl.theme.default.css' >"
        "<!-- owl.carousel JS============================================ -->"
        "<script src='/static/js/carousel/owl.carousel.min.js'></script>"
    )
