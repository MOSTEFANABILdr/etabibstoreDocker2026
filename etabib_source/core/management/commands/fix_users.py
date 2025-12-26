from django.contrib.auth.models import User, Group, Permission
from django.core.management import BaseCommand, CommandError

from core.enums import Role


class Command(BaseCommand):
    help = 'Fix end date in action'
    def handle(self, *args, **options):
        try:
            nb = 0
            na = 0
            nc = 0
            users = User.objects.all()
            for user in users:
                na += 1
                try:
                    perm = Permission.objects.get(codename="can_get_expo_badge")
                    user.user_permissions.remove(perm)
                    nc += 1
                except Exception as ex:
                    pass
                if hasattr(user, "professionnelsante"):
                    if user.groups.count() == 0:
                        nb += 1
                        user.groups.add(Group.objects.get(name=Role.VISITOR.value))
        except Exception as ex:
            raise CommandError("Error %s" % ex)

        self.stdout.write(self.style.SUCCESS('Successfully Fix user %s, %s from %s' % (nb, nc, na)))