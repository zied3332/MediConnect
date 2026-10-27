from django.utils import timezone

from .ai import BriefError
from .intake_ai import orient_patient
from .models import AIIntakeSession
from .intake_worker import app


@app.task(ignore_result=True, soft_time_limit=45, time_limit=50)
def generate_orientation(session_id):
    from .intake_views import specialty_catalog
    session = AIIntakeSession.objects.filter(pk=session_id, status='pending').first()
    if session is None:
        return
    target = AIIntakeSession.objects.filter(pk=session_id, status='pending')
    try:
        catalog = specialty_catalog()
        if not catalog:
            raise BriefError('unavailable')
        result, duration, model = orient_patient(session.answers, catalog)
        target.update(status='urgent' if result['urgent'] else 'ready', result=result, duration_ms=duration, model_name=model, updated_at=timezone.now())
    except BriefError as error:
        target.update(status='failed', error_code=error.code, updated_at=timezone.now())
    except Exception:
        # No patient text, credentials or provider payload in logs.
        target.update(status='failed', error_code='unavailable', updated_at=timezone.now())
