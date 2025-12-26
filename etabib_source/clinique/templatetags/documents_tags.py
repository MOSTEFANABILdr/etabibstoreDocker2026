import re

from django import template

from clinique.models import Document

register = template.Library()


@register.filter
def is_image(document):
    if isinstance(document, Document):
        regex = "([^\\s]+(\\.(?i)(jpe?g|png|gif|bmp))$)"

        # Compile the ReGex
        p = re.compile(regex)

        if document.fichier.name is None:
            return False

        if re.search(p, document.fichier.name):
            return True
        else:
            return False\

@register.filter
def is_audio(document):
    if isinstance(document, Document):
        regex = "([^\\s]+(\\.(?i)(wav|mp3|m4a))$)"

        # Compile the ReGex
        p = re.compile(regex)

        if document.fichier.name is None:
            return False

        if re.search(p, document.fichier.name):
            return True
        else:
            return False

@register.filter
def is_video(document):
    if isinstance(document, Document):
        regex = "([^\\s]+(\\.(?i)(mp4|avi|mov|wmv|avchd|mkv|webm))$)"

        # Compile the ReGex
        p = re.compile(regex)

        if document.fichier.name is None:
            return False

        if re.search(p, document.fichier.name):
            return True
        else:
            return False



