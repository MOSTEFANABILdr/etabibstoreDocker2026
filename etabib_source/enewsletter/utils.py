from enewsletter.models import Newsletter


def get_criteria_by_destination(destination):
    if Newsletter.DESTINATION_CHOICES[0][0] == destination:  # patient
        return get_criteria(["1", "3", "7"])
    if Newsletter.DESTINATION_CHOICES[1][0] == destination:  # Médecins
        return get_criteria(["1", "2", "3", "5", "6", "7"])
    if Newsletter.DESTINATION_CHOICES[2][0] == destination:  # Client
        return get_criteria(["1", "2", "3", "6", "7"])
    if Newsletter.DESTINATION_CHOICES[3][0] == destination:  # User
        return get_criteria(["4", "7"])
    if Newsletter.DESTINATION_CHOICES[4][0] == destination:  # Contact
        return get_criteria(["7"])
    return []


def get_criteria(choicies):
    return [list(item) for item in Newsletter.CRITERIA_CHOICES if item[0] in choicies]
