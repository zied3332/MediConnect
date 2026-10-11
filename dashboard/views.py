from django.shortcuts import render


def overview(request):
    """
    Admin dashboard overview.

    Uses demonstration data until the backend modules
    are connected.
    """
    context = {
        "page_title": "Overview",
        "stats": [
            {"label": "Total patients", "value": "1,248", "change": "+12.5%", "icon": "users"},
            {"label": "Active doctors", "value": "86", "change": "+4.2%", "icon": "doctors"},
            {"label": "Appointments", "value": "324", "change": "+8.1%", "icon": "calendar"},
            {"label": "Pending approvals", "value": "12", "change": "Needs review", "icon": "pending"},
        ],
        "recent_activity": [
            {"title": "New doctor registration", "description": "A doctor submitted a verification request.", "time": "10 minutes ago"},
            {"title": "Appointment booked", "description": "A new consultation was scheduled.", "time": "25 minutes ago"},
            {"title": "New patient account", "description": "A patient joined MediConnect.", "time": "1 hour ago"},
        ],
    }

    return render(request, "dashboard/overview.html", context)