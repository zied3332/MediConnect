from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("specialty", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="specialty",
            options={
                "db_table": "core_specialty",
                "ordering": ("name",),
                "verbose_name_plural": "Specialties",
            },
        ),
    ]
