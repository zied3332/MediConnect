from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render


# ──────────────────────────────────────────────
# Role guard decorator
# ──────────────────────────────────────────────

def role_required(*roles):
    """Combine @login_required with a role whitelist."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url="accounts:login")
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                return HttpResponseForbidden(
                    "<h2>403 — Access denied</h2>"
                    "<p>You don't have permission to view this page.</p>"
                    f'<a href="{request.user.dashboard_url}">Go to your dashboard →</a>'
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ──────────────────────────────────────────────
# Admin dashboard
# ──────────────────────────────────────────────

@role_required("admin")
def admin_overview(request):
    context = {
        "page_title": "Overview",
        "dashboard_role": "admin",
        "stats": [
            {"label": "Total patients",      "value": "1,248", "change": "+12.5%",       "icon": "P"},
            {"label": "Active doctors",      "value": "86",    "change": "+4.2%",        "icon": "D"},
            {"label": "Appointments",        "value": "324",   "change": "+8.1%",        "icon": "C"},
            {"label": "Pending approvals",   "value": "12",    "change": "Needs review", "icon": "!"},
        ],
        "recent_activity": [
            {"title": "New doctor registration",  "description": "A doctor submitted a verification request.", "time": "10 min ago"},
            {"title": "Appointment booked",       "description": "A new consultation was scheduled.",         "time": "25 min ago"},
            {"title": "New patient account",      "description": "A patient joined MediConnect.",             "time": "1 hour ago"},
        ],
    }
    return render(request, "dashboard/admin/overview.html", context)


# ──────────────────────────────────────────────
# Doctor dashboard
# ──────────────────────────────────────────────

@role_required("doctor")
def doctor_overview(request):
    context = {
        "page_title": "My Dashboard",
        "dashboard_role": "doctor",
        "stats": [
            {"label": "Today's appointments", "value": "8",   "change": "Next at 10:00",  "icon": "C"},
            {"label": "Total patients",       "value": "134", "change": "+3 this week",   "icon": "P"},
            {"label": "Pending reviews",      "value": "5",   "change": "Needs response", "icon": "R"},
            {"label": "Avg. rating",          "value": "4.8", "change": "From 97 reviews","icon": "★"},
        ],
        "upcoming_appointments": [
            {"patient": "Marie Dupont",   "time": "10:00 AM", "type": "General consultation"},
            {"patient": "Jean Martin",    "time": "11:30 AM", "type": "Follow-up"},
            {"patient": "Sophie Bernard", "time": "2:00 PM",  "type": "First visit"},
        ],
    }
    return render(request, "dashboard/doctor/overview.html", context)


# ──────────────────────────────────────────────
# Patient dashboard
# ──────────────────────────────────────────────

@role_required("patient")
def patient_overview(request):
    context = {
        "page_title": "My Health",
        "dashboard_role": "patient",
        "stats": [
            {"label": "Upcoming appointments", "value": "2", "change": "Next: Tomorrow", "icon": "C"},
            {"label": "Doctors seen",          "value": "4", "change": "Since joining",  "icon": "D"},
            {"label": "Prescriptions",         "value": "3", "change": "1 renewal due",  "icon": "Rx"},
            {"label": "Messages",              "value": "1", "change": "Unread",          "icon": "✉"},
        ],
        "upcoming_appointments": [
            {"doctor": "Dr. Amara Diallo", "specialty": "Cardiology",   "date": "Tomorrow — 9:00 AM"},
            {"doctor": "Dr. Lucas Petit",  "specialty": "Dermatology",  "date": "Nov 5 — 3:30 PM"},
        ],
    }
    return render(request, "dashboard/patient/overview.html", context)
