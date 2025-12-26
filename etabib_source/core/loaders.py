from django.template.loaders.app_directories import Loader as AppDirLoader
from django.template.utils import get_app_template_dirs


class AppDirV1Loader(AppDirLoader):
    def get_dirs(self):
        return get_app_template_dirs("templates/v1")


class AppDirV2Loader(AppDirLoader):
    def get_dirs(self):
        return get_app_template_dirs("templates/v2")
