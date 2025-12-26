from django.apps import AppConfig


class DrugsConfig(AppConfig):
    name = 'drugs'
    def ready(self):
        import drugs.signals
