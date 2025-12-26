'''
Created on 01 jav 2019

@author: ZAHI
'''

from django import template
from django.utils import timezone

from core.models import Action, DetailAction
from django.utils.translation import gettext as _

register = template.Library()


@register.filter
def is_active_tracking(action):
    if isinstance(action, Action):
        if action.type == "1":
            return True
    elif isinstance(action, str):
        if action == "1":
            return True
    else:
        return False


@register.filter
def is_punctual_tracking(action):
    if isinstance(action, Action):
        if action.type == "2":
            return True
    elif isinstance(action, str):
        if action == "2":
            return True
    else:
        return False


@register.filter
def is_tech_intervention(action):
    if isinstance(action, Action):
        if action.type == "3":
            return True
    elif isinstance(action, str):
        if action == "3":
            return True
    else:
        return False


@register.filter
def is_formation(action):
    if isinstance(action, Action):
        if action.type == "4":
            return True
    elif isinstance(action, str):
        if action == "4":
            return True
    else:
        return False

@register.filter
def is_commercial_request(action):
    if isinstance(action, Action):
        if action.type == "5":
            return True
    elif isinstance(action, str):
        if action == "5":
            return True
    else:
        return False


@register.filter
def renderActionStatus(action, **kwargs):
    if action.active:
        type = '<i class="fa fa-2x fa-close red" ></i>'
    else:
        type = '<i class="fa fa-2x fa-check green" ></i>'
    return type


@register.simple_tag
def timelinePanelCssClass(detail, **kwargs):
    if isinstance(detail, DetailAction):
        if detail.type:
            if detail.type in (DetailAction.TYPE_CHOICES_CMR[0][0], DetailAction.TYPE_CHOICES_CMR[1][0],
                               DetailAction.TYPE_CHOICES_CMR[2][0], DetailAction.TYPE_CHOICES_CMR[3][0],
                               DetailAction.TYPE_CHOICES_CMR[4][0]):
                return "timeline-panel-navy"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[5][0]:
                return "timeline-panel-red"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[6][0]:
                return "timeline-panel-marron"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[7][0]:
                return "timeline-panel-green"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[8][0]:
                return "timeline-panel-orange"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[9][0]:
                return "timeline-panel-aqua"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[10][0]:
                return "timeline-panel-olive"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[11][0]:
                return "timeline-panel-gray"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[12][0]:
                return "timeline-panel-blue"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[13][0]:
                return "timeline-panel-fuchsia"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[14][0]:
                return "timeline-panel-fuchsia"
            if detail.type == DetailAction.TYPE_CHOICES_CMN[0][0]:
                return "timeline-panel-purple"
            if detail.type == DetailAction.TYPE_CHOICES_TEC[0][0]:
                return "timeline-panel-marron"
        else:
            if hasattr(object, "facture"):
                return "timeline-panel-gray"


@register.simple_tag
def timelineBadgeCssClass(detail, **kwargs):
    if isinstance(detail, DetailAction):
        if detail.type:
            if detail.type in (DetailAction.TYPE_CHOICES_CMR[0][0], DetailAction.TYPE_CHOICES_CMR[1][0],
                               DetailAction.TYPE_CHOICES_CMR[2][0], DetailAction.TYPE_CHOICES_CMR[3][0],
                               DetailAction.TYPE_CHOICES_CMR[4][0]):
                return "navy"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[5][0]:
                return "red"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[6][0]:
                return "marron"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[7][0]:
                return "green"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[8][0]:
                return "orange"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[9][0]:
                return "aqua"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[10][0]:
                return "olive"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[11][0]:
                return "gray"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[12][0]:
                return "blue"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[13][0]:
                return "fuchsia"
            if detail.type == DetailAction.TYPE_CHOICES_CMR[14][0]:
                return "fuchsia"
            if detail.type == DetailAction.TYPE_CHOICES_CMN[0][0]:
                return "purple"
            if detail.type == DetailAction.TYPE_CHOICES_TEC[0][0]:
                return "marron"
        else:
            if hasattr(detail, "facture"):
                return "gray"
            if hasattr(object, "clotureaction"):
                return "check"


@register.simple_tag
def pisteEndDateCssClass(action, **kwargs):
    """
    check end date of an action(piste) with now datetime
    :param action:
    :param kwargs:
    :return: css class
    """
    if isinstance(action, Action):
        now = timezone.now().date()
        if action.date_fin == now:
            return "blue"
        elif action.date_fin > now:
            return "green"
        elif action.date_fin < now:
            return "red"
