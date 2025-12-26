from rest_framework import serializers

from smsgateway import utils
from smsgateway.models import Sms


class SmsStatusSerializer(serializers.Serializer):
    deviceId = serializers.CharField(max_length=255)
    messageId = serializers.CharField(max_length=255)
    status = serializers.CharField(max_length=255)
    action = serializers.CharField(max_length=255)

    def save(self):
        messageId = self.validated_data['messageId']
        status = self.validated_data['status']
        sms = Sms.objects.get(id=messageId)
        if (status == "SENT"):
            sms.status = "2"
        elif (status == "DELIVERED"):
            sms.status = 3
        elif (status == "RECEIVED"):
            sms.status = 4
        sms.save()
        pass


class SmsSerializer(serializers.ModelSerializer):
    messageId = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    number = serializers.SerializerMethodField()
    sim = serializers.SerializerMethodField()

    def get_messageId(self, obj):
        return "%s" % obj.id

    def get_message(self, obj):
        if obj.smsmodel:
            return "%s" % obj.smsmodel.message
        elif obj.message:
            return "%s" % obj.message
        elif obj.template:
            return "%s" % obj.template.content

    def get_number(self, obj):
        return "%s" % utils.correct_numbers(obj.source)

    def get_sim(self, obj):
        return "%s" % obj.sim

    class Meta:
        model = Sms
        fields = ["message", "number", "messageId", "sim"]
