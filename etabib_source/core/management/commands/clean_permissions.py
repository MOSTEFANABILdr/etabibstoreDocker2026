import django.apps
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Remove custom permissions that are no longer in models'

    def handle(self, *args, **options):
        default_perm_names = list()
        # are real perms in db, may not be accurate
        db_custom_perm_names = list()
        # will be used to ensure they are correct.
        meta_custom_perm_names = list()

        default_and_custom_perms = list()

        for model in django.apps.apps.get_models():
            # add to models found to fix perms from removed models
            app_label = model._meta.app_label
            lower_model_name = model._meta.model_name

            all_model_permissions = Permission.objects.filter(content_type__app_label=app_label, content_type__model=lower_model_name)


            default_and_custom_perms.extend([x for x in all_model_permissions])
            # get the custom meta permissions, these should be in the meta of the class
            # will be a list or tuple or list, [0=codename, 1=name]
            meta_permissions = model._meta.permissions

            if meta_permissions:
                for perm in all_model_permissions:
                    # will be the model name from the content type, this is how django makes default perms
                    # we are trying to remove them so now we can figure out which ones are default by provided name
                    model_name_lower = perm.content_type.name
                    # default_perms =  ['add', 'change', 'view', 'delete', 'undelete']
                    # append them to the list of default names
                    default_perm_names.append(f'Can add {model_name_lower}')
                    default_perm_names.append(f'Can change {model_name_lower}')
                    default_perm_names.append(f'Can view {model_name_lower}')
                    default_perm_names.append(f'Can delete {model_name_lower}')
                    default_perm_names.append(f'Can undelete {model_name_lower}')
                    # will mean this is a custom perm...so add it
                    if not perm.name in default_perm_names:
                        db_custom_perm_names.append(perm.codename)

                # the perms to ensure are correct...
                for model_perm in meta_permissions:
                    # get the meta perm, will be a list or tuple or list, [0=codename, 1=name]
                    custom_perm = Permission.objects.get(codename=model_perm[0])
                    meta_custom_perm_names.append(custom_perm.codename)


        perms_to_remove = [perm for perm in db_custom_perm_names if perm not in meta_custom_perm_names]
        if not perms_to_remove:
            print('There are no stale custom permissions to remove.')


        print(perms_to_remove)
        #now remove the custom permissions that were removed from the model
        for actual_permission_to_remove in Permission.objects.filter(codename__in=perms_to_remove):
            # print(actual_permission_to_remove)
            actual_permission_to_remove.delete()
            print(actual_permission_to_remove, '...deleted')
