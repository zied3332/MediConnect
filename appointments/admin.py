from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("start", "patient", "doctor", "mode", "status", "no_show_risk", "reminder_sent")
    list_filter = ("status", "mode", "risk_status")
    search_fields = ("patient__email", "doctor__email", "reason")
    date_hierarchy = "start"
    raw_id_fields = ("patient", "doctor")
