from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.decorators import is_professionnal


@login_required
@is_professionnal
def AppointmentEvents(request):
    conext = {
        'sidebar_appoinments': True
    }
    return render(request, "events.html", conext)