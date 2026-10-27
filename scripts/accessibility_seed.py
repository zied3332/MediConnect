"""Create synthetic audit fixtures only in the isolated audit database."""
import os
os.environ["DJANGO_SETTINGS_MODULE"] = "config.accessibility_settings"
import django
django.setup()

from datetime import time, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from accounts.models import DoctorProfile
from availability.models import Availability
from specialty.models import Specialty
from appointments.models import Appointment
from consultations.models import Consultation
from medical_records.models import DossierMedical, Ordonnance, Examen
import json

assert str(settings.DATABASES["default"]["NAME"]).endswith(".audit.sqlite3")
User = get_user_model()
specialty, _ = Specialty.objects.get_or_create(name="Audit General Medicine")
users = {}
for role in ("patient", "doctor", "admin"):
    user, _ = User.objects.get_or_create(email=f"audit-{role}@example.invalid", defaults={
        "username": f"audit-{role}", "role": role, "first_name": "Audit", "last_name": role.title(),
    })
    user.set_password("Local-audit-2026!")
    user.main_specialty = specialty if role == "doctor" else None
    user.save()
    users[role] = user
DoctorProfile.objects.get_or_create(user=users["doctor"], defaults={"specialty": "general_medicine", "status": "approved"})
for weekday in range(7):
    Availability.objects.get_or_create(doctor=users["doctor"], weekday=weekday, start_time=time(9), end_time=time(17))
record, _ = DossierMedical.objects.get_or_create(patient=users["patient"], defaults={"antecedents": "Synthetic audit record", "allergies": "Synthetic example"})
for i in range(14):
    appointment, _ = Appointment.objects.get_or_create(patient=users["patient"], doctor=users["doctor"], reason=f"Synthetic audit appointment {i}", defaults={
        "start": timezone.now() - timedelta(days=i+1), "status": "completed", "no_show_risk": .7, "risk_status": "ready"})
    consultation, _ = Consultation.objects.get_or_create(appointment=appointment, defaults={"diagnostic": "Synthetic audit consultation"})
    Ordonnance.objects.get_or_create(consultation=consultation, defaults={"medicaments": "Synthetic audit prescription"})
Examen.objects.get_or_create(dossier=record, titre="Synthetic audit examination", defaults={"fichier": "audit-placeholder.pdf"})
cookies = {}
for role, user in users.items():
    client = Client()
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
    cookies[role] = client.cookies["sessionid"].value
settings.BASE_DIR.joinpath(".audit-sessions.json").write_text(json.dumps(cookies))
print("Synthetic fixtures created; patient ID:", users["patient"].pk)
