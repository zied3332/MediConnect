import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.apps import apps

selected_apps = [
    "accounts",
    "core",
    "appointments",
    "consultations",
    "medical_records",
]

with open("mediconnect_schema.txt", "w", encoding="utf-8") as output:
    for model in apps.get_models():
        if model._meta.app_label not in selected_apps:
            continue

        output.write(f"\n{'=' * 65}\n")
        output.write(f"MODEL: {model._meta.label}\n")
        output.write(f"TABLE: {model._meta.db_table}\n")
        output.write(f"{'=' * 65}\n")

        for field in model._meta.get_fields():
            field_type = field.get_internal_type()
            relation = ""

            if field.is_relation and field.related_model:
                relation = f" -> {field.related_model._meta.label}"

            output.write(
                f"{field.name}: {field_type}"
                f" | null={getattr(field, 'null', 'N/A')}"
                f" | unique={getattr(field, 'unique', 'N/A')}"
                f"{relation}\n"
            )

print("Schema exported successfully to mediconnect_schema.txt")
