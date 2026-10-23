from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# Decorators
# ─────────────────────────────────────────────────────────────────────────────

def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url="accounts:login")
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                return HttpResponseForbidden(
                    "<h2>403 — Access denied</h2>"
                    f'<a href="{request.user.dashboard_url}">Go to your dashboard →</a>'
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def approved_doctor_required(view_func):
    @wraps(view_func)
    @login_required(login_url="accounts:login")
    def wrapper(request, *args, **kwargs):
        user = request.user
        if user.role != "doctor":
            return HttpResponseForbidden(
                "<h2>403 — Access denied</h2>"
                f'<a href="{user.dashboard_url}">Go to your dashboard →</a>'
            )
        try:
            profile = user.doctor_profile
        except Exception:
            return redirect("accounts:doctor_status")
        if not profile.can_access_dashboard:
            return redirect("accounts:doctor_status")
        return view_func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# Admin — Overview
# ─────────────────────────────────────────────────────────────────────────────

@role_required("admin")
def admin_overview(request):
    from accounts.models import DoctorProfile

    pending_count = DoctorProfile.objects.filter(
        status=DoctorProfile.Status.PENDING_REVIEW
    ).count()

    context = {
        "page_title": "Overview",
        "dashboard_role": "admin",
        "active_nav": "overview",
        "stats": [
            {"label": "Total patients",    "value": "1,248", "change": "+12.5%",       "icon": "P"},
            {"label": "Active doctors",    "value": "86",    "change": "+4.2%",        "icon": "D"},
            {"label": "Appointments",      "value": "324",   "change": "+8.1%",        "icon": "C"},
            {"label": "Pending approvals", "value": str(pending_count), "change": "Needs review", "icon": "!"},
        ],
        "recent_activity": [
            {"title": "New doctor registration",  "description": "A doctor submitted a verification request.", "time": "10 min ago"},
            {"title": "Appointment booked",       "description": "A new consultation was scheduled.",         "time": "25 min ago"},
            {"title": "New patient account",      "description": "A patient joined MediConnect.",             "time": "1 hour ago"},
        ],
        "pending_doctors": DoctorProfile.objects.filter(
            status=DoctorProfile.Status.PENDING_REVIEW
        ).select_related("user").order_by("-submitted_at")[:5],
    }
    return render(request, "dashboard/admin/overview.html", context)


# ─────────────────────────────────────────────────────────────────────────────
# Admin — Doctor applications list
# ─────────────────────────────────────────────────────────────────────────────

@role_required("admin")
def admin_doctor_list(request):
    from accounts.models import DoctorProfile

    status_filter = request.GET.get("status", "")
    qs = DoctorProfile.objects.select_related("user").order_by("-submitted_at", "-created_at")
    if status_filter:
        qs = qs.filter(status=status_filter)

    counts = {
        "all":               DoctorProfile.objects.count(),
        "pending_review":    DoctorProfile.objects.filter(status="pending_review").count(),
        "needs_more_info":   DoctorProfile.objects.filter(status="needs_more_info").count(),
        "approved":          DoctorProfile.objects.filter(status="approved").count(),
        "rejected":          DoctorProfile.objects.filter(status="rejected").count(),
        "pending_documents": DoctorProfile.objects.filter(status="pending_documents").count(),
    }

    context = {
        "page_title": "Doctor Applications",
        "dashboard_role": "admin",
        "active_nav": "doctors",
        "profiles": qs,
        "status_filter": status_filter,
        "counts": counts,
        "status_choices": DoctorProfile.Status.choices,
    }
    return render(request, "dashboard/admin/doctor_list.html", context)


# ─────────────────────────────────────────────────────────────────────────────
# Admin — Doctor application detail + review actions
# ─────────────────────────────────────────────────────────────────────────────

@role_required("admin")
def admin_doctor_detail(request, pk):
    from accounts.models import DoctorProfile

    profile = get_object_or_404(DoctorProfile.objects.select_related("user"), pk=pk)

    if request.method == "POST":
        action = request.POST.get("action")
        now = timezone.now()

        if action == "approve":
            profile.status = DoctorProfile.Status.APPROVED
            profile.reviewed_at = now
            profile.rejection_reason = ""
            profile.save(update_fields=["status", "reviewed_at", "rejection_reason"])
            profile.user.is_active = True
            profile.user.save(update_fields=["is_active"])
            messages.success(
                request,
                f"Dr. {profile.user.get_full_name()} has been approved."
            )
            return redirect("dashboard:admin_doctor_list")

        elif action == "reject":
            reason = request.POST.get("rejection_reason", "").strip()
            if not reason:
                messages.error(request, "Please provide a rejection reason.")
            else:
                profile.status = DoctorProfile.Status.REJECTED
                profile.reviewed_at = now
                profile.rejection_reason = reason
                profile.save(update_fields=["status", "reviewed_at", "rejection_reason"])
                profile.user.is_active = False
                profile.user.save(update_fields=["is_active"])
                messages.success(
                    request,
                    f"Dr. {profile.user.get_full_name()}'s application has been rejected."
                )
                return redirect("dashboard:admin_doctor_list")

        elif action == "needs_more_info":
            note = request.POST.get("reviewer_note", "").strip()
            if not note:
                messages.error(request, "Please write a message for the doctor.")
            else:
                profile.status = DoctorProfile.Status.NEEDS_MORE_INFO
                profile.reviewer_note = note
                profile.save(update_fields=["status", "reviewer_note"])
                messages.success(
                    request,
                    f"Dr. {profile.user.get_full_name()} has been asked for more info."
                )
                return redirect("dashboard:admin_doctor_list")

    context = {
        "page_title": "Review Application",
        "dashboard_role": "admin",
        "active_nav": "doctors",
        "profile": profile,
    }
    return render(request, "dashboard/admin/doctor_detail.html", context)


# ─────────────────────────────────────────────────────────────────────────────
# Doctor dashboard (approved only)
# ─────────────────────────────────────────────────────────────────────────────

@approved_doctor_required
def doctor_overview(request):
    context = {
        "page_title": "My Dashboard",
        "dashboard_role": "doctor",
        "active_nav": "overview",
        "stats": [
            {"label": "Today's appointments", "value": "8",   "change": "Next at 10:00",   "icon": "C"},
            {"label": "Total patients",       "value": "134", "change": "+3 this week",    "icon": "P"},
            {"label": "Pending reviews",      "value": "5",   "change": "Needs response",  "icon": "R"},
            {"label": "Avg. rating",          "value": "4.8", "change": "From 97 reviews", "icon": "★"},
        ],
        "upcoming_appointments": [
            {"patient": "Marie Dupont",   "time": "10:00 AM", "type": "General consultation"},
            {"patient": "Jean Martin",    "time": "11:30 AM", "type": "Follow-up"},
            {"patient": "Sophie Bernard", "time": "2:00 PM",  "type": "First visit"},
        ],
    }
    return render(request, "dashboard/doctor/overview.html", context)


# ─────────────────────────────────────────────────────────────────────────────
# Patient dashboard
# ─────────────────────────────────────────────────────────────────────────────

@role_required("patient")
def patient_overview(request):
    context = {
        "page_title": "My Health",
        "dashboard_role": "patient",
        "active_nav": "overview",
        "stats": [
            {"label": "Upcoming appointments", "value": "2", "change": "Next: Tomorrow", "icon": "C"},
            {"label": "Doctors seen",          "value": "4", "change": "Since joining",  "icon": "D"},
            {"label": "Prescriptions",         "value": "3", "change": "1 renewal due",  "icon": "Rx"},
            {"label": "Messages",              "value": "1", "change": "Unread",         "icon": "✉"},
        ],
        "upcoming_appointments": [
            {"doctor": "Dr. Amara Diallo", "specialty": "Cardiology",  "date": "Tomorrow — 9:00 AM"},
            {"doctor": "Dr. Lucas Petit",  "specialty": "Dermatology", "date": "Nov 5 — 3:30 PM"},
        ],
    }
    return render(request, "dashboard/patient/overview.html", context)
