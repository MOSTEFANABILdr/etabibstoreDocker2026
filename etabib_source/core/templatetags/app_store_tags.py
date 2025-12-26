'''
Created on 30 déc. 2018

@author: ZAHI
'''
from django import template
from core.models import ModuleStatus
from django.utils.translation import gettext as _

register = template.Library()


@register.filter(name='isvisible')
def isVisible(value):
    return False if value == ModuleStatus.NO_VERSION.value else True


@register.filter(name='getinstallationaction')
def getInstallationAction(value, app, poste,session=None):
    if value == ModuleStatus.IS_INSTALLED.value:
        return _("Uninstall")
    if value == ModuleStatus.TO_INSTALL.value:
        return _("Cancel the installation")
    if value == ModuleStatus.TO_UNINSTALL.value:
        return _("Cancel the uninstallation")
    if value == ModuleStatus.NOT_INSTALLED.value:
        if session:
            from basket.templatetags.carton_tags import wasAddedToCart
            if not wasAddedToCart(app, session, poste):
                return _("Ajouter au panier")
            else:
                return _("Retirer du panier")


@register.filter(name='getinstallationsuccessmessage')
def getInstallationSuccessMessage(value, app, poste, session=None):
    if value == ModuleStatus.IS_INSTALLED.value:
        return _("L'opération s'est bien déroulée")
    if value == ModuleStatus.TO_INSTALL.value:
        return _("L'opération s'est bien déroulée")
    if value == ModuleStatus.TO_UNINSTALL.value:
        return _("L'opération s'est bien déroulée")
    if value == ModuleStatus.NOT_INSTALLED.value:
        if session:
            from basket.templatetags.carton_tags import wasAddedToCart
            if not wasAddedToCart(app, session, poste):
                return _("L'opération s'est bien déroulée")
            else:
                return _("L'opération s'est bien déroulée")



@register.filter(name='getinstallationtext')
def getInstallationText(value, app, poste,session=None):
    if value == ModuleStatus.IS_INSTALLED.value:
        return _("Voulez-vous désinstaller l'application %s ?") % app.libelle
    if value == ModuleStatus.TO_INSTALL.value:
        return _("Voulez-vous annuler l'installation de l'application %s ?") % app.libelle
    if value == ModuleStatus.TO_UNINSTALL.value:
        return _("Voulez-vous annuler la désinstallation de l'application %s ?") % app.libelle
    if value == ModuleStatus.NOT_INSTALLED.value:
        if session:
            from basket.templatetags.carton_tags import wasAddedToCart
            if not wasAddedToCart(app, session, poste):
                return _("Voulez-vous ajouter l'application %s au panier?") % app.libelle
            else:
                return _("Voulez-vous retirer l'application %s du panier?") % app.libelle

