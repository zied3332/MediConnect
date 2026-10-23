from django.contrib import admin

from .models import Availability, Specialty


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name", "description")


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ("doctor", "weekday", "start_time", "end_time", "is_free")
    list_filter = ("weekday", "is_free")
    search_fields = ("doctor__email", "doctor__first_name", "doctor__last_name")
