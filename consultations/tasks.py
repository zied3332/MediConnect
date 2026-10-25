from celery import shared_task
from django.utils import timezone

from .ai import BriefError, generate_cards, source_data, source_hash
from .models import PatientBrief


@shared_task(ignore_result=True, soft_time_limit=65, time_limit=70)
def generate_patient_brief(brief_id, generation_id):
    brief = PatientBrief.objects.select_related("consultation").filter(pk=brief_id, generation_id=generation_id, status="pending").first()
    if brief is None:
        return
    expected_hash = brief.source_hash
    target = PatientBrief.objects.filter(pk=brief_id, generation_id=generation_id, status="pending")
    try:
        if source_hash(brief.consultation) != expected_hash:
            raise BriefError("source_changed")
        cards, duration, model = generate_cards(source_data(brief.consultation))
        brief.consultation.refresh_from_db()
        if source_hash(brief.consultation) != expected_hash:
            raise BriefError("source_changed")
        target.update(status="ready", cards=cards, duration_ms=duration, model_name=model, error_code="", updated_at=timezone.now())
    except BriefError as error:
        target.update(status="failed", error_code=error.code, updated_at=timezone.now())
    except Exception:
        # Do not persist or log the exception: provider responses may include health data.
        target.update(status="failed", error_code="unavailable", updated_at=timezone.now())
