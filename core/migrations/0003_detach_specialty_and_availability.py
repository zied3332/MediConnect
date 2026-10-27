from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_availability"),
        ("specialty", "0001_initial"),
        ("availability", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="Availability"),
                migrations.DeleteModel(name="Specialty"),
            ],
            database_operations=[],
        ),
    ]
