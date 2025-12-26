import hashlib

import basehash
import jwt
from django.contrib.auth.models import User

from core.enums import Role
from etabibWebsite import settings
from filesharing.enums import PatientFileType


def getPatientFileTypeName(type):
    for item in PatientFileType:
        if item.value[0] == type:
            return item.value[1]
    return ""


def generateUniqueUserId(profile_id, role):
    """
    concatenate two hashed strings
    - the first string "{0}_patient" where {0} is the identify of the server, hashed with md5 function
    - the second string is the profile_id, hashed with basehash (reversible hash)
    :param profile_id: is the id of the profile
    :return:
    """
    pre_str_format = None
    hash_fn = basehash.base56(32)
    if role == Role.PATIENT:
        pre_str_format = "{0}_patient"
    elif role == Role.DOCTOR:
        pre_str_format = "{0}_doctor"
    elif role in (Role.PHARMACIST.value, Role.TEACHER.value, Role.RESEARCHER.value, Role.COMPUTER_SCIENCE.value,
                Role.COMM_MARKETING.value, Role.MEDICAL_COMPANY_MANAGER.value, Role.MEDICAL_PURCHASING_MANAGER.value,
                Role.BIOLOGISTE.value, Role.PARAMEDICAL.value, Role.AUXILIARY.value, Role.PSYCHOLOGIST.value,
                Role.MINISTRY.value, Role.ADMINISTRATION.value, Role.STUDENT.value, Role.DENTIST.value):
        pre_str_format = "{0}_professional"
    if pre_str_format:
        pre_str = pre_str_format.format(settings.SH_LOCAL_SERVER_IDENTITY)
        hashed_pre_str = hashlib.md5(pre_str.encode("utf-8")).hexdigest()
        hashed_str = "{0}_{1}".format(
            hashed_pre_str, hash_fn.hash(profile_id)
        )
        return hashed_str
    return None


def decryptUserUiqueId(encryptedProfileId, role):
    pre_str_format = None
    hash_fn = basehash.base56(32)
    if role == Role.PATIENT:
        pre_str_format = "{0}_patient"
    elif role == Role.DOCTOR:
        pre_str_format = "{0}_doctor"
    elif role in (Role.PHARMACIST.value, Role.TEACHER.value, Role.RESEARCHER.value, Role.COMPUTER_SCIENCE.value,
                Role.COMM_MARKETING.value, Role.MEDICAL_COMPANY_MANAGER.value, Role.MEDICAL_PURCHASING_MANAGER.value,
                Role.BIOLOGISTE.value, Role.PARAMEDICAL.value, Role.AUXILIARY.value, Role.PSYCHOLOGIST.value,
                Role.MINISTRY.value, Role.ADMINISTRATION.value, Role.STUDENT.value, Role.DENTIST.value):
        pre_str_format = "{0}_professional"
    if pre_str_format:
        pre_str = pre_str_format.format(settings.SH_LOCAL_SERVER_IDENTITY)
        hashed_pre_str = hashlib.md5(pre_str.encode("utf-8")).hexdigest()
        if hashed_pre_str not in encryptedProfileId:
            raise Exception("Not a valid encrypted id")
        hashed_profile_id = encryptedProfileId.split("{0}_".format(hashed_pre_str))[1]
        return hash_fn.unhash(hashed_profile_id)
    return None


def generateAuthenticationJwtToken(user):
    if user and isinstance(user, User):
        care_team_ids = []
        if hasattr(user, "patient"):
            for es in user.patient.equipe_soins.filter(confirme=True):
                if es.professionnel:
                    if hasattr(es.professionnel, "medecin"):
                        care_team_ids.append(generateUniqueUserId(es.professionnel.medecin.id, Role.DOCTOR))
                    elif hasattr(es.professionnel, "professionnelsante"):
                        care_team_ids.append(generateUniqueUserId(es.professionnel.professionnelsante.id, Role.PHARMACIST))
        else:#medecin or professionnelsante
            for es in user.equipesoins_set.filter(confirme=True):
                if es.patient:
                    care_team_ids.append(generateUniqueUserId(es.patient.id, Role.PATIENT))
        cxt = {
            "context": {
                "user": {
                    "id": generateUniqueUserId(user.patient.id, Role.PATIENT) if hasattr(
                        user, "patient"
                    ) else generateUniqueUserId(user.medecin.id, Role.DOCTOR) if hasattr(
                        user, "medecin"
                    ) else generateUniqueUserId(user.professionnelsante.id, Role.PHARMACIST) if hasattr(
                        user, "professionnelsante"
                    ) else None,
                    "care_team_ids": care_team_ids
                }
            },
            "aud": settings.SH_JWT_AUDIENCE,
            "iss": settings.SH_JWT_ISSUER,
            "sub": "store.etabib.dz",
        }
        encoded_token = jwt.encode(
            cxt,
            settings.SH_JWT_APP_SECRET,
            algorithm='HS256'
        )
        return encoded_token
