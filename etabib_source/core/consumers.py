import json
import traceback

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.urls import reverse

from basket.cart import Cart
from basket.templatetags.carton_tags import cartCounts
from core.enums import WebsocketCommand
from core.models import Medecin, Patient
from core.utils import getUserNotification, hasEnoughMoney
from etabibWebsite import settings
from teleconsultation.decorators import touch_presence
from teleconsultation.models import Room, Tdemand, Presence


class NotificationConsumer(WebsocketConsumer):
    def connect(self):
        if self.scope["user"].is_anonymous:
            # Reject the connection
            self.close()
        else:
            self.room_group_name = 'chat_%s' % self.scope["user"].id
            # to track users presences
            if hasattr(self.scope["user"], "medecin"):
                if "3" in self.scope["user"].medecin.current_services:
                    Room.objects.add(settings.DOCTORS_CHANNEL, self.room_group_name, self.scope["user"])
            if hasattr(self.scope["user"], "patient"):
                Room.objects.add(settings.PATIENTS_CHANNEL, self.room_group_name, self.scope["user"])

            # Join room group
            async_to_sync(self.channel_layer.group_add)(
                self.room_group_name,
                self.channel_name
            )
            # Accept the connection
            self.accept()

    def disconnect(self, close_code):
        if hasattr(self.scope["user"], "medecin"):
            Room.objects.remove(settings.DOCTORS_CHANNEL, self.room_group_name)
        if hasattr(self.scope["user"], "patient"):
            Room.objects.remove(settings.PATIENTS_CHANNEL, self.room_group_name)

        # Leave room group
        if not self.scope["user"].is_anonymous:
            async_to_sync(self.channel_layer.group_discard)(
                self.room_group_name,
                self.channel_name
            )

    @touch_presence
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        command = text_data_json['command']
        user = self.scope['user']

        if command == WebsocketCommand.FETCH_NOTIFICATIONS.value:
            notify_count, notify_list_html = getUserNotification(user)
            data = {
                'command': command,
                'notify_count': notify_count,
                'notify_list_html': notify_list_html
            }

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'notification_message',
                    'data': data
                }
            )
        elif command == WebsocketCommand.NEW_ROCKCHAT_MESSAGE.value:
            title = text_data_json['title']
            text = text_data_json['text']
            data = {
                'command': WebsocketCommand.NEW_NOTIFICATION.value,
                'title': title,
                'content': text,
                "delay": 2000,
                "icon": "/static/img/logo/ihsm.png",
                "url": reverse('rocketchat'),
                "notif_type": "success",
                "sound": True,
                "delayIndicator": False
            }

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'notification_message',
                    'data': data
                }
            )

        elif command == WebsocketCommand.TELECONSULTATION_DEMAND.value:
            if 'medecin_id' in text_data_json:
                medecin_id = text_data_json['medecin_id']
                if medecin_id:
                    try:
                        medecin = Medecin.objects.get(id=medecin_id)

                        # reject the request if the user sends many requests in a short time
                        # if TeleconsultationDemand.is_rejected(user):
                        #     cmd = WebsocketCommand.TELECONSULTATION_DEMAND_REJECTED.value
                        #     async_to_sync(self.channel_layer.group_send)(
                        #         self.room_group_name,
                        #         {
                        #             'type': 'notification_message',
                        #             'data': {
                        #                 'command': cmd,
                        #                 'code': "TOO_MANY_REQUEST",
                        #             }
                        #         }
                        #     )
                        #     return

                        # checking if patient has enough money to do a consultation
                        rejected = not hasEnoughMoney(user.patient, medecin)

                        if rejected:
                            cmd = WebsocketCommand.TELECONSULTATION_DEMAND_REJECTED.value
                            async_to_sync(self.channel_layer.group_send)(
                                self.room_group_name,
                                {
                                    'type': 'notification_message',
                                    'data': {
                                        'command': cmd,
                                        'code': "NOT_ENOUGH_MONEY",
                                    }
                                }
                            )
                            return

                        # checking if the doctor is OFFLINE
                        if not Presence.objects.filter(user=medecin.user).exists():
                            cmd = WebsocketCommand.TELECONSULTATION_DEMAND_REJECTED.value
                            async_to_sync(self.channel_layer.group_send)(
                                self.room_group_name,
                                {
                                    'type': 'notification_message',
                                    'data': {
                                        'command': cmd,
                                        'code': "OFFLINE",
                                    }
                                }
                            )
                            return

                        # Cheking if the doctor is BUSY
                        if medecin.is_busy():
                            cmd = WebsocketCommand.TELECONSULTATION_DEMAND_REJECTED.value
                            async_to_sync(self.channel_layer.group_send)(
                                self.room_group_name,
                                {
                                    'type': 'notification_message',
                                    'data': {
                                        'command': cmd,
                                        'code': "BUSY",
                                    }
                                }
                            )
                            return
                        # Cheking if the doctor has another demand
                        q = Tdemand.objects.filter(medecin__id=medecin_id)
                        if q.count() > 0:
                            d = Tdemand.objects.filter(medecin__id=medecin_id).latest('id')
                            if d:
                                if d.is_still_valid():
                                    cmd = WebsocketCommand.TELECONSULTATION_DEMAND_REJECTED.value
                                    async_to_sync(self.channel_layer.group_send)(
                                        self.room_group_name,
                                        {
                                            'type': 'notification_message',
                                            'data': {
                                                'command': cmd,
                                                'code': "BUSY",
                                            }
                                        }
                                    )
                                    return

                        # else Notify the doctor
                        tDemand = Tdemand()
                        tDemand.patient = user.patient
                        tDemand.medecin = medecin
                        tDemand.save()
                    except Medecin.DoesNotExist as e:
                        traceback.print_exc()
            elif 'patient_id' in text_data_json:
                patientId = text_data_json['patient_id']
                if patientId:
                    patient = Patient.objects.get(id=patientId)
                    tDemand = Tdemand()
                    tDemand.patient = patient
                    tDemand.medecin = user.medecin
                    tDemand.from_patient = False
                    tDemand.save()

        elif command == WebsocketCommand.TELECONSULTATION_DEMAND_CANCELED.value:
            if 'medecin_id' in text_data_json:
                medecin_id = text_data_json['medecin_id']
                demand = Tdemand.objects.filter(
                    medecin__id=medecin_id,
                    patient__user=user,
                    rendez_vous__isnull=True).latest('id')
                if demand:
                    demand.annulee = True
                    demand.save()
            if 'patient_id' in text_data_json:
                patient_id = text_data_json['patient_id']
                demand = Tdemand.objects.filter(
                    patient__id=patient_id,
                    medecin__user=user,
                    rendez_vous__isnull=True).latest('id')
                if demand:
                    demand.annulee = True
                    demand.save()
        elif command == WebsocketCommand.FETCH_CART_COUNTS.value:
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'notification_message',
                    'data': {
                        'command': WebsocketCommand.FETCH_CART_COUNTS.value,
                    }
                }
            )

    # Receive message from room group
    def notification_message(self, event):

        data = event['data']
        command = data['command']
        if command == WebsocketCommand.FETCH_NOTIFICATIONS.value:
            self.send(text_data=json.dumps({
                'command': command,
                'notify_count': data['notify_count'],
                'notify_list_html': data['notify_list_html']
            }))
        elif command == WebsocketCommand.FETCH_CART_COUNTS.value:
            count = None
            if 'count' in data:
                count = data['count']
            self.send(text_data=json.dumps({
                'command': command,
                'cart_count': count if count else cartCounts(self.scope["session"])
            }))
        elif command == WebsocketCommand.NEW_NOTIFICATION.value:
            content = data['content']
            icon = data['icon']
            title = data['title']
            url = data['url']
            delay = data['delay']
            self.send(text_data=json.dumps({
                'command': command,
                'notify_count': data.get('notify_count', ""),
                'notify_list_html': data.get('notify_list_html', ""),
                'title': title,
                'new_notification_content': content,
                'icon': icon,
                'is_a_call': data.get('is_a_call', False),
                'is_patient': data.get('is_patient', False),
                'redirect_url': data.get('redirect_url', url),
                'notif_title': data.get('notif_title', ""),
                'notif_body': data.get('notif_body', ""),
                'tdemand_id': data.get('tdemand_id', ""),
                'notif_type': data.get('notif_type', "info"),
                'sound': data.get('sound', False),
                'delayIndicator': data.get('delayIndicator', True),
                'url': url,
                'delay': delay,
            }))
        elif command == WebsocketCommand.TELECONSULTATION_DEMAND_ACCEPTED.value:
            self.send(text_data=json.dumps({
                'command': command,
                'url': data['url'],
                'doctor': data['doctor'],
                'room': data['room'],
            }))
        elif command == WebsocketCommand.TELECONSULTATION_DEMAND_REJECTED.value:
            self.send(text_data=json.dumps({
                'command': command,
                'code': data['code']
            }))
        # elif command == "TELECONSULTATION_GET_ONLINE_DOCTORS_COUNT":
        #     self.send(text_data=json.dumps({
        #         'command': command,
        #         'counts': data['count']
        #     }))
