import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class Hl7Serializer(serializers.Serializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac = self.context.get("mac")
