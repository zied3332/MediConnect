from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from consultations.models import AIIntakeSession


class Command(BaseCommand):
    help = 'Delete orientation sessions older than seven days (private answers included).'

    def handle(self, *args, **options):
        count, _ = AIIntakeSession.objects.filter(created_at__lt=timezone.now()-timedelta(days=7)).delete()
        self.stdout.write(f'{count} orientation sessions deleted.')
