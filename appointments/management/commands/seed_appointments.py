from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import DoctorProfile, User
from appointments import services
from appointments.models import Appointment
from appointments.tasks import compute_no_show_risk
from availability.models import Availability
from specialty.models import Specialty
from notifications.models import Notification
from notifications.services import notify

PASSWORD = "Demo1234!"
DOMAIN = "mediconnect.demo"

DOCTORS = [
    ("amara.diallo", "Amara", "Diallo", "Cardiology", "cardiology"),
    ("lucas.petit", "Lucas", "Petit", "Dermatology", "dermatology"),
    ("sofia.benali", "Sofia", "Benali", "General Medicine", "general_medicine"),
]
PATIENTS = [
    ("marie.dupont", "Marie", "Dupont"),
    ("jean.martin", "Jean", "Martin"),
    ("sophie.bernard", "Sophie", "Bernard"),
]
# Monday-Friday 09:00-12:00 and 14:00-17:00, Saturday morning.
WEEKLY_HOURS = [(d, "09:00", "12:00") for d in range(6)] + [(d, "14:00", "17:00") for d in range(5)]


class Command(BaseCommand):
    help = "Create demo users, availability and appointments in every status (safe to run again)."

    def handle(self, *args, **options):
        from config.celery import app

        # Run the risk task inline even when no Celery worker/Redis is running.
        app.conf.CELERY_TASK_ALWAYS_EAGER = True  # namespaced key wins over task_always_eager

        with transaction.atomic():
            admin = self._user("admin", "Admin", "MediConnect", User.Role.ADMIN, is_staff=True, is_superuser=True)
            doctors = [self._doctor(*spec) for spec in DOCTORS]
            patients = [self._user(u, f, l, User.Role.PATIENT) for u, f, l in PATIENTS]

            demo_users = [admin, *doctors, *patients]
            Appointment.objects.filter(patient__in=patients).delete()
            Appointment.objects.filter(doctor__in=doctors).delete()
            Notification.objects.filter(user__in=demo_users).delete()

            created = self._appointments(doctors, patients)

        for appointment in Appointment.objects.filter(pk__in=[a.pk for a in created]):
            compute_no_show_risk(appointment.pk)
        reminders = services.send_due_reminders()

        self._report(admin, doctors, patients, reminders)

    # ── Users ────────────────────────────────────────────────────────────
    def _user(self, username, first, last, role, **extra):
        email = f"{username}@{DOMAIN}"
        # Username = email so it can never clash with an existing account (e.g. "admin").
        user, _ = User.objects.update_or_create(
            email=email,
            defaults={"username": email, "first_name": first, "last_name": last, "role": role,
                      "is_active": True, **extra},
        )
        user.set_password(PASSWORD)
        user.save()
        return user

    def _doctor(self, username, first, last, specialty_name, specialty_code):
        specialty, _ = Specialty.objects.get_or_create(name=specialty_name)
        doctor = self._user(username, first, last, User.Role.DOCTOR, main_specialty=specialty)
        DoctorProfile.objects.update_or_create(
            user=doctor,
            defaults={"specialty": specialty_code, "status": DoctorProfile.Status.APPROVED,
                      "reviewed_at": timezone.now()},
        )
        doctor.availability_slots.all().delete()
        Availability.objects.bulk_create(
            Availability(doctor=doctor, weekday=day, start_time=start, end_time=end)
            for day, start, end in WEEKLY_HOURS
        )
        return doctor

    # ── Appointments ─────────────────────────────────────────────────────
    def _slot(self, doctor, min_hours, skip=0):
        """A free slot of the doctor at least `min_hours` from now."""
        limit = timezone.now() + timedelta(hours=min_hours)
        slots = [s for s in services.get_free_slots(doctor, days=21) if s >= limit]
        return slots[min(skip, len(slots) - 1)]

    def _past(self, days, hour):
        day = timezone.localdate() - timedelta(days=days)
        return timezone.make_aware(datetime.combine(day, time(hour, 0)))

    def _soon(self, hours):
        """Rounded to the half hour; used for reminder demos (may be outside opening hours)."""
        moment = timezone.now() + timedelta(hours=hours)
        return moment.replace(minute=0 if moment.minute < 30 else 30, second=0, microsecond=0)

    def _appointments(self, doctors, patients):
        amara, lucas, sofia = doctors
        marie, jean, sophie = patients
        created = []

        def past(patient, doctor, days, hour, status, reason, booked_days_before=7):
            appointment = Appointment.objects.create(
                patient=patient, doctor=doctor, start=self._past(days, hour), status=status, reason=reason,
                reminder_sent=True, risk_status=Appointment.RiskStatus.PENDING,
            )
            Appointment.objects.filter(pk=appointment.pk).update(
                created_at=appointment.start - timedelta(days=booked_days_before)
            )
            created.append(appointment)
            return appointment

        # History (also feeds the AI features: Jean often misses appointments).
        past(marie, amara, 30, 9, Appointment.Status.COMPLETED, "Annual heart check-up")
        past(marie, sofia, 12, 10, Appointment.Status.COMPLETED, "Flu symptoms", 2)
        past(jean, amara, 40, 10, Appointment.Status.NO_SHOW, "Palpitations", 30)
        past(jean, lucas, 25, 15, Appointment.Status.NO_SHOW, "Skin rash", 20)
        past(jean, sofia, 15, 11, Appointment.Status.COMPLETED, "Back pain", 5)
        past(sophie, lucas, 8, 14, Appointment.Status.NO_SHOW, "Mole check", 25)
        # Confirmed but already started: the doctor can mark it completed / no-show.
        past(sophie, sofia, 1, 9, Appointment.Status.CONFIRMED, "Blood test results", 6)

        def book(patient, doctor, start, reason, mode=Appointment.Mode.CABINET):
            appointment = services.book_appointment(patient, doctor, start, mode, reason)
            created.append(appointment)
            return appointment

        # Pending requests waiting for the doctor.
        book(marie, amara, self._slot(amara, 48), "Follow-up after the check-up", Appointment.Mode.VISIO)
        book(jean, amara, self._slot(amara, 24 * 9), "Chest pain when running")
        book(sophie, lucas, self._slot(lucas, 72), "Eczema flare-up")

        # Confirmed upcoming.
        confirmed = book(marie, lucas, self._slot(lucas, 24 * 5), "Acne treatment review")
        services.confirm_appointment(confirmed, lucas)
        confirmed = book(jean, sofia, self._slot(sofia, 24 * 4), "Persistent cough", Appointment.Mode.VISIO)
        services.confirm_appointment(confirmed, sofia)

        # Rejected and cancelled.
        rejected = book(sophie, amara, self._slot(amara, 24 * 6, skip=2), "Second opinion")
        services.reject_appointment(rejected, amara, "Please see your general doctor first.")
        cancelled = book(marie, sofia, self._slot(sofia, 24 * 7), "Vaccination")
        services.cancel_appointment(cancelled, marie)

        # Reminder demos: confirmed within 24h, and a high-risk one within 48h.
        for patient, doctor, hours, reason, risk in [
            (sophie, amara, 20, "Blood pressure control", None),
            (jean, lucas, 36, "Allergy test", 0.82),
        ]:
            appointment = Appointment.objects.create(
                patient=patient, doctor=doctor, start=self._soon(hours), reason=reason,
                status=Appointment.Status.CONFIRMED, risk_status=Appointment.RiskStatus.PENDING,
            )
            if risk is not None:
                Appointment.objects.filter(pk=appointment.pk).update(
                    no_show_risk=risk, risk_status=Appointment.RiskStatus.READY
                )
            else:
                created.append(appointment)

        for patient in patients:
            notify(patient, "Welcome to MediConnect! You can now book appointments online.",
                   Notification.Type.SYSTEM, "/appointments/book/")
        return created

    # ── Output ───────────────────────────────────────────────────────────
    def _report(self, admin, doctors, patients, reminders):
        out = self.stdout.write
        counts = {label: Appointment.objects.filter(status=value, doctor__in=doctors).count()
                  for value, label in Appointment.Status.choices}
        risks = Appointment.objects.filter(doctor__in=doctors, no_show_risk__isnull=False).count()
        out(self.style.SUCCESS("Demo data ready."))
        out("Appointments: " + ", ".join(f"{label} {n}" for label, n in counts.items()))
        out(f"AI risk computed for {risks} appointments "
            "(0 means the model is missing: run python manage.py train_noshow_model).")
        out(f"Reminders sent: {reminders['reminders']} (24h), {reminders['early_reminders']} (48h high risk)")
        out("")
        out(f"Demo logins (password for every account: {PASSWORD})")
        out(f"  {'Role':<9}{'Email':<34}Name")
        for user in [admin, *doctors, *patients]:
            name = user.get_full_name()
            if user.role == User.Role.DOCTOR:
                name = f"Dr. {name} ({user.main_specialty})"
            out(f"  {user.get_role_display():<9}{user.email:<34}{name}")
        out("")
        out("Login page: http://127.0.0.1:8000/accounts/login/")
