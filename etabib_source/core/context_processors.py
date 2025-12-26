from core.forms.patient_forms import AdvancedSearchForm


def advanced_search(request):
    q = request.GET.get("q", "")
    specialite_q_id = request.GET.get("specialite_q", "")
    city_q_id = request.GET.get("city_q", "")
    return {'AdvancedSearchForm': AdvancedSearchForm(initial={
        "q": q or "", "specialite_q": specialite_q_id or "", "city_q": city_q_id or ""
    })}