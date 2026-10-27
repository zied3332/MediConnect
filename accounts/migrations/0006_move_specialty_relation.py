from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_merge_20261027_1154"),
        ("specialty", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="main_specialty",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="doctors",
                to="specialty.specialty",
            ),
        )
    ]
