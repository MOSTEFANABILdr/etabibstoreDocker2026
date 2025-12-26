from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http.response import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _


def is_registered(the_func):
    def _decorated(request, *args, **kwargs):
        profiles = ["medecin", "partenaire", "patient", "organisateur", "professionnelsante"]
        if all(not hasattr(request.user, attr) for attr in profiles):
            return the_func(request, *args, **kwargs)
        else:
            raise Http404

    return _decorated


def is_doctor(the_func):
    def _decorated(request, *args, **kwargs):
        if hasattr(request.user, 'medecin'):
            if request.user.medecin.carte:
                if request.user.medecin.checked:
                    return the_func(request, *args, **kwargs)
                elif request.user.medecin.rejected:
                    return redirect("card-rejected")
                else:
                    return redirect("doctor-account-validation")
            else:
                return redirect("doctor-identity")
        else:
            raise Http404

    return _decorated


def is_not_verified_doctor(the_func):
    def _decorated(request, *args, **kwargs):
        if hasattr(request.user, 'medecin'):
            if not request.user.medecin.carte:
                return the_func(request, *args, **kwargs)
            raise Http404
        else:
            raise Http404

    return _decorated


def is_not_verified_professionnal(the_func):
    def _decorated(request, *args, **kwargs):
        if hasattr(request.user, 'professionnelsante'):
            if not request.user.professionnelsante.carte:
                return the_func(request, *args, **kwargs)
            elif request.user.professionnelsante.rejected:
                return redirect("card-rejected")
            elif not request.user.professionnelsante.checked:
                return redirect("professional-account-validation")
            raise Http404
        else:
            raise Http404

    return _decorated


def is_professionnal(the_func):
    def _decorated(request, *args, **kwargs):
        if hasattr(request.user, 'professionnelsante'):
            if request.user.professionnelsante.carte:
                if request.user.professionnelsante.checked:
                    return the_func(request, *args, **kwargs)
                elif request.user.professionnelsante.rejected:
                    return redirect("card-rejected")
                else:
                    return redirect("professional-account-validation")
            else:
                return redirect("professional-identity")
        else:
            raise Http404

    return _decorated


def is_doctor_or_professionnal(the_func):
    def _decorated(request, *args, **kwargs):
        if hasattr(request.user, 'medecin'):
            if request.user.medecin.carte:
                if request.user.medecin.checked:
                    return the_func(request, *args, **kwargs)
                elif request.user.medecin.rejected:
                    return redirect("card-rejected")
                else:
                    return redirect("doctor-account-validation")
            else:
                return redirect("doctor-identity")
        if hasattr(request.user, 'professionnelsante'):
            if request.user.professionnelsante.carte:
                if request.user.professionnelsante.checked:
                    return the_func(request, *args, **kwargs)
                elif request.user.professionnelsante.rejected:
                    return redirect("card-rejected")
                else:
                    return redirect("professional-account-validation")
            else:
                return redirect("professional-identity")
        else:
            raise Http404

    return _decorated


def is_operator(the_func):
    def _decorated(request, *args, **kwargs):
        if hasattr(request.user, 'operateur'):
            return the_func(request, *args, **kwargs)
        raise PermissionDenied()

    return _decorated


def is_partner(the_func):
    def _decorated(request, *args, **kwargs):
        if hasattr(request.user, 'partenaire'):
            if request.user.partenaire.verifie:
                return the_func(request, *args, **kwargs)
            else:
                return redirect("partner-account-validation")
        else:
            raise PermissionDenied()

    return _decorated


def is_patient(the_func):
    def _decorated(request, *args, **kwargs):
        # redirect user to fill his profile if is empty
        if request.path_info != reverse("patient-profile"):
            if not request.user.first_name and not request.user.last_name:
                messages.warning(
                    request,
                    _("Veuillez remplir votre profile.")
                )
                return redirect("patient-profile")
        if hasattr(request.user, 'patient'):
            return the_func(request, *args, **kwargs)
        raise PermissionDenied()

    return _decorated


def is_organizer(the_func):
    def _decorated(request, *args, **kwargs):
        if hasattr(request.user, 'organisateur'):
            return the_func(request, *args, **kwargs)
        raise PermissionDenied()

    return _decorated


def is_speaker(the_func):
    def _decorated(request, *args, **kwargs):
        if hasattr(request.user, 'speaker'):
            return the_func(request, *args, **kwargs)
        raise PermissionDenied()

    return _decorated


def is_moderator(the_func):
    def _decorated(request, *args, **kwargs):
        if hasattr(request.user, 'moderateur'):
            return the_func(request, *args, **kwargs)
        raise PermissionDenied()

    return _decorated


def skip_signal():
    def _skip_signal(signal_func):
        @wraps(signal_func)
        def _decorator(sender, instance, **kwargs):
            if hasattr(instance, 'skip_signal'):
                return None
            return signal_func(sender, instance, **kwargs)

        return _decorator

    return _skip_signal


# use: @has_access(EtabibService.ETABIB_CARE, EtabibService.ONLINE_AGENDA)
def has_access(service):
    def _check_access(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            no_access = True
            if hasattr(request.user, "medecin"):
                if request.user.medecin.has_access(service.value):
                    no_access = False

            if no_access:
                messages.warning(request, _("Désolé, votre abonnement ne contient pas ce service"))
                if hasattr(request.user, "medecin"):
                    return redirect("doctor-offers")
                else:
                    raise PermissionDenied()
            return view_func(request, *args, **kwargs)

        return wrapper

    return _check_access


def v2_only(the_func):
    def _decorated(request, *args, **kwargs):
        if request.template_version == "v1":
            raise Http404
        return the_func(request, *args, **kwargs)

    return _decorated


def v1_only(the_func):
    def _decorated(request, *args, **kwargs):
        if request.template_version == "v2":
            raise Http404
        return the_func(request, *args, **kwargs)

    return _decorated
