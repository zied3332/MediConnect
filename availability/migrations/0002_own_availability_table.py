from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("availability", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="availability",
            options={
                "db_table": "core_availability",
                "ordering": ("doctor", "weekday", "start_time"),
            },
        ),
    ]
