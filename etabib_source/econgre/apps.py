from django.apps import AppConfig


class EcongreConfig(AppConfig):
    name = 'econgre'
    def ready(self):
        import econgre.signals