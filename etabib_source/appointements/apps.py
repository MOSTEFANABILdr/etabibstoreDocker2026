from django.apps import AppConfig


class AppointementsConfig(AppConfig):
    name = 'appointements'
    def ready(self):
        import appointements.signals
