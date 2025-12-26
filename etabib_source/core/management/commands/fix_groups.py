from django.contrib.auth.models import User, Group, Permission
from django.core.management import BaseCommand, CommandError

from core.enums import Role
from core.models import OffrePrepaye


class Command(BaseCommand):
    help = 'Fix Offers'
    def handle(self, *args, **options):
        try:
            nb = 0
            na = 0
            nc = 0
            groups = Group.objects.all()
            for group in groups:
                na += 1
                if group.name not in [Role.COMMERCIAL.value, Role.COMMUNICATION.value, Role.TECHNICIAN.value,
                                      Role.PARTNER.value, Role.PATIENT.value, Role.ORGANISATEUR.value,
                                      Role.SPEAKER.value,
                                      Role.MODERATOR.value]:
                    if group.name == Role.DOCTOR.value:
                        perm = Permission.objects.get(codename="can_view_etabib_econgre")
                        group.permissions.add(perm)

                        perm = Permission.objects.get(codename="can_veiw_e_prescription")
                        group.permissions.add(perm)

                        perm = Permission.objects.get(codename="can_veiw_teleconsultation")
                        group.permissions.add(perm)

                        perm = Permission.objects.get(codename="can_veiw_agenda")
                        group.permissions.add(perm)

                        perm = Permission.objects.get(codename="can_veiw_etabib_file_sharing")
                        group.permissions.add(perm)

                    perm = Permission.objects.get(codename="care_can_view_dashboard")
                    group.permissions.add(perm)

                    perm = Permission.objects.get(codename="care_can_view_profile")
                    group.permissions.add(perm)

                    perm = Permission.objects.get(codename="can_view_etabib_expos")
                    group.permissions.add(perm)

                    perm = Permission.objects.get(codename="can_view_etabib_store")
                    group.permissions.add(perm)


                nc += 1

        except Exception as ex:
            raise CommandError("Error %s" % ex)

        self.stdout.write(self.style.SUCCESS('Successfully Fix %s offers from %s' % (nc, na)))