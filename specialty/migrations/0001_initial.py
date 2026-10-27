from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("core", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Specialty",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=120, unique=True)),
                ("description", models.TextField(blank=True)),
            ],
            options={
                "db_table": "core_specialty",
                "managed": False,
                "ordering": ("name",),
                "verbose_name_plural": "Specialties",
            },
        )
    ]
