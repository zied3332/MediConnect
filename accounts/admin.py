from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.html import format_html

from .models import DoctorProfile, User


# ── User admin ────────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "first_name", "last_name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    fieldsets = BaseUserAdmin.fieldsets + (
        ("MediConnect", {"fields": ("role",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email", "username", "first_name", "last_name",
                    "role", "password1", "password2",
                ),
            },
        ),
    )


# ── Doctor profile admin ──────────────────────────────────────────────────────

def _file_link(label, field_value):
    """Return an HTML link to a file field, or a dash if empty."""
    if field_value:
        return format_html('<a href="{}" target="_blank">View {}</a>', field_value.url, label)
    return "—"


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = (
        "doctor_name", "specialty", "status_badge",
        "submitted_at", "reviewed_at",
    )
    list_filter = ("status", "specialty")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    readonly_fields = (
        "doctor_name", "doctor_email", "created_at", "updated_at",
        "submitted_at", "reviewed_at",
        "medical_license_link", "diploma_link",
        "national_id_link", "selfie_link",
    )
    ordering = ("-submitted_at",)

    fieldsets = (
        ("Doctor", {
            "fields": ("doctor_name", "doctor_email", "specialty"),
        }),
        ("Status", {
            "fields": ("status", "rejection_reason", "reviewer_note"),
        }),
        ("Documents", {
            "fields": (
                "medical_license_link",
                "diploma_link",
                "national_id_link",
                "selfie_link",
            ),
        }),
        ("Timestamps", {
            "fields": ("created_at", "submitted_at", "reviewed_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["approve_doctors", "reject_doctors", "request_more_info"]

    # ── Computed display fields ──────────────────────────────────────────

    @admin.display(description="Doctor")
    def doctor_name(self, obj):
        return obj.user.get_full_name()

    @admin.display(description="Email")
    def doctor_email(self, obj):
        return obj.user.email

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "pending_documents": "#f0ad4e",
            "pending_review":    "#5bc0de",
            "needs_more_info":   "#d9534f",
            "approved":          "#5cb85c",
            "rejected":          "#777",
        }
        color = colors.get(obj.status, "#aaa")
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 9px;'
            'border-radius:12px;font-size:11px;font-weight:700;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description="Medical license")
    def medical_license_link(self, obj):
        return _file_link("medical license", obj.medical_license)

    @admin.display(description="Diploma")
    def diploma_link(self, obj):
        return _file_link("diploma", obj.diploma)

    @admin.display(description="National ID / passport")
    def national_id_link(self, obj):
        return _file_link("national ID", obj.national_id)

    @admin.display(description="Selfie with ID")
    def selfie_link(self, obj):
        return _file_link("selfie", obj.selfie_with_id)

    # ── Bulk actions ─────────────────────────────────────────────────────

    @admin.action(description="✅ Approve selected doctors")
    def approve_doctors(self, request, queryset):
        now = timezone.now()
        updated = 0
        for profile in queryset:
            profile.status = DoctorProfile.Status.APPROVED
            profile.reviewed_at = now
            profile.save(update_fields=["status", "reviewed_at"])
            # Allow the user to log in.
            profile.user.is_active = True
            profile.user.save(update_fields=["is_active"])
            updated += 1
        self.message_user(
            request,
            f"{updated} doctor(s) approved and activated.",
            messages.SUCCESS,
        )

    @admin.action(description="❌ Reject selected doctors")
    def reject_doctors(self, request, queryset):
        now = timezone.now()
        for profile in queryset:
            profile.status = DoctorProfile.Status.REJECTED
            profile.reviewed_at = now
            profile.save(update_fields=["status", "reviewed_at"])
            profile.user.is_active = False
            profile.user.save(update_fields=["is_active"])
        self.message_user(
            request,
            f"{queryset.count()} doctor(s) rejected.",
            messages.WARNING,
        )

    @admin.action(description="ℹ️ Request more info from selected doctors")
    def request_more_info(self, request, queryset):
        for profile in queryset:
            profile.status = DoctorProfile.Status.NEEDS_MORE_INFO
            profile.save(update_fields=["status"])
        self.message_user(
            request,
            f"{queryset.count()} doctor(s) flagged for more info.",
            messages.INFO,
        )
