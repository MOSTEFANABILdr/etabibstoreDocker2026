from django.db import models
from django.utils import timezone
from polymorphic.managers import PolymorphicManager
from polymorphic.query import PolymorphicQuerySet


class SoftDeleteQuerySet(PolymorphicQuerySet):
    def delete(self):
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()


class SoftPolyMorphDeleteManager(PolymorphicManager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, self._db).filter(deleted_at__isnull=True)


class NonArchivedContactManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(archive=False)


class ArchivedContactManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(archive=True)


class AllContactManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()
