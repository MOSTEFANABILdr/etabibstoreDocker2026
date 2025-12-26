
from django.db import migrations, models


def forwards_func(apps, schema_editor):
    # Get the database connection
    connection = schema_editor.connection

    # Execute the SQL code to update the 'unique_id' column in 'drugs_laboratoire' table
    for i in range(14):
        sql_code = f"UPDATE `drugs_formehomogene` SET `unique_id` = '{i}' WHERE `drugs_formehomogene`.`id` = {i}"
        with connection.cursor() as cursor:
            cursor.execute(sql_code)


class Migration(migrations.Migration):
    dependencies = [
        ('drugs', '0010_makti'),
    ]
    operations = [
        migrations.AddField(
            model_name='formehomogene',
            name='unique_id',
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.RunPython(forwards_func),
    ]
