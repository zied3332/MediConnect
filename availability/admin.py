from django.contrib import admin

from .models import Availability


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ("doctor", "weekday", "start_time", "end_time", "is_free")
    list_filter = ("weekday", "is_free")

