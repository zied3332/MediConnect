from celery import shared_task

from .models import Appointment


@shared_task
def compute_no_show_risk(appointment_id):
    """Score one appointment with the AI model and store the result."""
    from .ml.predictor import predict_risk

    appointment = Appointment.objects.filter(pk=appointment_id).first()
    if appointment is None:
        return None
    risk = predict_risk(appointment)
    if risk is None:
        Appointment.objects.filter(pk=appointment_id).update(risk_status=Appointment.RiskStatus.FAILED)
        return None
    Appointment.objects.filter(pk=appointment_id).update(
        no_show_risk=risk, risk_status=Appointment.RiskStatus.READY
    )
    return risk


@shared_task
def send_reminders():
    """Hourly (Celery beat): 24h reminders + extra 48h reminder for high risk."""
    from .services import send_due_reminders

    return send_due_reminders()
