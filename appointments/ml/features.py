"""
Features for the no-show model.

They are computable both from the Kaggle dataset ("Medical Appointment No
Shows", KaggleV2-May-2016.csv) and from our Appointment model, so the model
trained on the dataset can score real bookings:

    lead_days           days between booking and appointment
    weekday             0 = Monday ... 6 = Sunday
    prior_appointments  patient's earlier appointments whose outcome was known at booking time
    prior_no_shows      how many of those were no-shows
    reminder_sent       1 if a reminder was sent (SMS_received in the dataset)

History only counts appointments that took place strictly before the booking
day, so the model never sees the future.
"""

FEATURES = ["lead_days", "weekday", "prior_appointments", "prior_no_shows", "reminder_sent"]

DATASET_COLUMNS = {"PatientId", "ScheduledDay", "AppointmentDay", "SMS_received", "No-show"}


def appointment_features(appointment):
    """Feature dict for one Appointment instance."""
    from django.utils import timezone

    from appointments.models import Appointment

    booked = timezone.localtime(appointment.created_at or timezone.now())
    start = timezone.localtime(appointment.start)

    history = Appointment.objects.filter(
        patient_id=appointment.patient_id,
        start__date__lt=booked.date(),
        status__in=(Appointment.Status.COMPLETED, Appointment.Status.NO_SHOW),
    ).exclude(pk=appointment.pk)

    return {
        "lead_days": max((start.date() - booked.date()).days, 0),
        "weekday": start.weekday(),
        "prior_appointments": history.count(),
        "prior_no_shows": history.filter(status=Appointment.Status.NO_SHOW).count(),
        "reminder_sent": int(bool(appointment.reminder_sent)),
    }


def dataset_features(df):
    """
    Build (X, y) from the raw Kaggle dataframe.
    y = 1 when the patient did not show up.
    """
    import pandas as pd

    missing = DATASET_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing columns: {', '.join(sorted(missing))}")

    df = df.copy()
    df["booked_day"] = pd.to_datetime(df["ScheduledDay"], utc=True).dt.normalize()
    df["appt_day"] = pd.to_datetime(df["AppointmentDay"], utc=True).dt.normalize()
    df["lead_days"] = (df["appt_day"] - df["booked_day"]).dt.days
    # A few rows are booked after the appointment day: data errors.
    df = df[df["lead_days"] >= 0].copy()

    df["weekday"] = df["appt_day"].dt.weekday
    df["no_show"] = (df["No-show"].astype(str).str.strip().str.lower() == "yes").astype(int)
    df["reminder_sent"] = df["SMS_received"].astype(int)

    # Patient history known at booking time: appointments on a day strictly
    # before the booking day (merge_asof with allow_exact_matches=False).
    history = (
        df.groupby(["PatientId", "appt_day"])["no_show"]
        .agg(visits="size", misses="sum")
        .reset_index()
        .sort_values(["PatientId", "appt_day"])
    )
    history["prior_appointments"] = history.groupby("PatientId")["visits"].cumsum()
    history["prior_no_shows"] = history.groupby("PatientId")["misses"].cumsum()

    left = df.reset_index()[["index", "PatientId", "booked_day"]].sort_values("booked_day")
    right = history[["PatientId", "appt_day", "prior_appointments", "prior_no_shows"]].sort_values("appt_day")
    right = right.astype({"appt_day": left["booked_day"].dtype})
    merged = pd.merge_asof(
        left,
        right,
        left_on="booked_day",
        right_on="appt_day",
        by="PatientId",
        direction="backward",
        allow_exact_matches=False,
    ).set_index("index")

    df["prior_appointments"] = merged["prior_appointments"].reindex(df.index).fillna(0).astype(int)
    df["prior_no_shows"] = merged["prior_no_shows"].reindex(df.index).fillna(0).astype(int)

    return df[FEATURES].astype(int), df["no_show"]
