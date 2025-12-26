from django.apps import AppConfig


class TeleconsultationConfig(AppConfig):
    name = 'teleconsultation'
    def ready(self):
        import teleconsultation.signals
