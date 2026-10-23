from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from core.models import Availability, Specialty
from .forms import AvailabilityForm, DoctorAvailabilityForm, SpecialtyForm


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


@role_required("admin")
def admin_users(request):
    """Display and filter registered users for administrators."""
    search_query = request.GET.get("q", "").strip()
    selected_role = request.GET.get("role", "").strip()

    users = User.objects.all().order_by("-date_joined")
    if search_query:
        users = users.filter(
            Q(email__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(username__icontains=search_query)
        )
    if selected_role in User.Role.values:
        users = users.filter(role=selected_role)

    context = {
        "page_title": "Users",
        "dashboard_role": "admin",
        "users": users,
        "search_query": search_query,
        "selected_role": selected_role,
        "role_choices": User.Role.choices,
        "specialties": Specialty.objects.all(),
        "total_users": User.objects.count(),
    }
    return render(request, "dashboard/admin/users.html", context)


@role_required("admin")
def update_user_role(request, user_id):
    """Update a user's MediConnect role from the admin user table."""
    if request.method != "POST":
        return redirect("dashboard:admin_users")

    user = get_object_or_404(User, pk=user_id)
    role = request.POST.get("role", "")
    if role not in User.Role.values:
        messages.error(request, "Please select a valid user role.")
        return redirect("dashboard:admin_users")

    if user.role == role:
        messages.info(request, f"{user.get_full_name() or user.email} already has this role.")
    else:
        user.role = role
        user.save(update_fields=["role"])
        messages.success(
            request,
            f"{user.get_full_name() or user.email} is now a {user.get_role_display().lower()}.",
        )
    return redirect("dashboard:admin_users")


@role_required("admin")
def admin_specialties(request):
    if request.method == "POST":
        form = SpecialtyForm(request.POST)
        if form.is_valid():
            specialty = form.save()
            messages.success(request, f"{specialty.name} was added.")
            return redirect("dashboard:admin_specialties")
    else:
        form = SpecialtyForm()

    context = {
        "page_title": "Specialties",
        "dashboard_role": "admin",
        "form": form,
        "specialties": Specialty.objects.all(),
        "catalogue_specialties": Specialty.objects.all()[:4],
        "has_more_specialties": Specialty.objects.count() > 4,
        "doctors": User.objects.filter(role=User.Role.DOCTOR).select_related(
            "main_specialty"
        ),
    }
    return render(request, "dashboard/admin/specialties.html", context)


@role_required("admin")
def specialty_list(request):
    return render(
        request,
        "dashboard/admin/specialty_list.html",
        {
            "page_title": "Specialties",
            "dashboard_role": "admin",
            "specialties": Specialty.objects.all(),
        },
    )


@role_required("admin")
def edit_specialty(request, specialty_id):
    specialty = get_object_or_404(Specialty, pk=specialty_id)
    if request.method == "POST":
        form = SpecialtyForm(request.POST, instance=specialty)
        if form.is_valid():
            form.save()
            messages.success(request, f"{specialty.name} was updated.")
        else:
            messages.error(request, "Please correct the specialty details.")
    return redirect(request.POST.get("next") or "dashboard:specialty_list")


@role_required("admin")
def delete_specialty(request, specialty_id):
    if request.method == "POST":
        specialty = get_object_or_404(Specialty, pk=specialty_id)
        name = specialty.name
        specialty.delete()
        messages.success(request, f"{name} was deleted.")
    return redirect(request.POST.get("next") or "dashboard:specialty_list")


@role_required("admin")
def update_doctor_specialty(request, user_id):
    if request.method != "POST":
        return redirect("dashboard:admin_specialties")

    doctor = get_object_or_404(User, pk=user_id, role=User.Role.DOCTOR)
    specialty_id = request.POST.get("specialty")
    specialty = get_object_or_404(Specialty, pk=specialty_id) if specialty_id else None
    doctor.main_specialty = specialty
    doctor.save(update_fields=["main_specialty"])
    messages.success(request, f"{doctor.get_full_name() or doctor.email}'s specialty was updated.")
    return redirect("dashboard:admin_specialties")


@role_required("admin")
def admin_availability(request):
    context = {
        "page_title": "Availability",
        "dashboard_role": "admin",
        "slots": Availability.objects.select_related("doctor"),
    }
    return render(request, "dashboard/admin/availability.html", context)


@role_required("admin")
def delete_availability(request, slot_id):
    return redirect("dashboard:admin_availability")


@role_required("doctor")
def doctor_availability(request):
    if request.method == "POST":
        form = DoctorAvailabilityForm(request.POST, doctor=request.user)
        if form.is_valid():
            slot = form.save(commit=False)
            slot.doctor = request.user
            slot.full_clean()
            slot.save()
            messages.success(request, "Availability slot was added.")
            return redirect("dashboard:doctor_availability")
    else:
        form = DoctorAvailabilityForm(doctor=request.user)

    context = {
        "page_title": "Availability",
        "dashboard_role": "doctor",
        "form": form,
        "slots": request.user.availability_slots.all(),
    }
    return render(request, "dashboard/doctor/availability.html", context)


@role_required("doctor")
def edit_doctor_availability(request, slot_id):
    slot = get_object_or_404(
        Availability,
        pk=slot_id,
        doctor=request.user,
    )
    if request.method == "POST":
        form = DoctorAvailabilityForm(
            request.POST,
            instance=slot,
            doctor=request.user,
        )
        if form.is_valid():
            updated_slot = form.save(commit=False)
            updated_slot.doctor = request.user
            updated_slot.full_clean()
            updated_slot.save()
            messages.success(request, "Availability slot was updated.")
            return redirect("dashboard:doctor_availability")
    else:
        form = DoctorAvailabilityForm(instance=slot, doctor=request.user)

    return render(
        request,
        "dashboard/doctor/availability_form.html",
        {
            "page_title": "Availability",
            "dashboard_role": "doctor",
            "form": form,
            "slot": slot,
        },
    )


@role_required("doctor")
def delete_doctor_availability(request, slot_id):
    if request.method == "POST":
        slot = get_object_or_404(Availability, pk=slot_id, doctor=request.user)
        slot.delete()
        messages.success(request, "Availability slot was removed.")
    return redirect("dashboard:doctor_availability")


@role_required("doctor")
def toggle_doctor_availability(request, slot_id):
    if request.method == "POST":
        slot = get_object_or_404(Availability, pk=slot_id, doctor=request.user)
        slot.is_free = not slot.is_free
        slot.save(update_fields=["is_free"])
        messages.success(request, "Availability status was updated.")
    return redirect("dashboard:doctor_availability")


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
