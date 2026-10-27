from django.utils.translation import gettext_lazy as ui_gettext

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from dashboard.views import role_required

from .forms import DoctorAvailabilityForm
from .models import Availability


@role_required("admin")
def admin_availability(request):
    context = {
        "page_title": ui_gettext("Availability"),
        "dashboard_role": "admin",
        "slots": Availability.objects.select_related("doctor"),
    }

    return render(
        request,
        "dashboard/admin/availability.html",
        context,
    )


@role_required("admin")
def delete_availability(request, slot_id):
    return redirect("availability:admin_availability")


@role_required("doctor")
def doctor_availability(request):
    if request.method == "POST":
        form = DoctorAvailabilityForm(
            request.POST,
            doctor=request.user,
        )

        if form.is_valid():
            slot = form.save(commit=False)
            slot.doctor = request.user
            slot.full_clean()
            slot.save()

            messages.success(
                request,
                ui_gettext("Availability slot was added."),
            )

            return redirect("availability:doctor_availability")
    else:
        form = DoctorAvailabilityForm(
            doctor=request.user
        )

    context = {
        "page_title": ui_gettext("Availability"),
        "dashboard_role": "doctor",
        "form": form,
        "slots": request.user.availability_slots.all(),
    }

    return render(
        request,
        "dashboard/doctor/availability.html",
        context,
    )


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

            messages.success(
                request,
                ui_gettext("Availability slot was updated."),
            )

            return redirect("availability:doctor_availability")
    else:
        form = DoctorAvailabilityForm(
            instance=slot,
            doctor=request.user,
        )

    return render(
        request,
        "dashboard/doctor/availability_form.html",
        {
            "page_title": ui_gettext("Availability"),
            "dashboard_role": "doctor",
            "form": form,
            "slot": slot,
        },
    )


@role_required("doctor")
def delete_doctor_availability(request, slot_id):
    if request.method == "POST":
        slot = get_object_or_404(
            Availability,
            pk=slot_id,
            doctor=request.user,
        )

        slot.delete()

        messages.success(
            request,
            ui_gettext("Availability slot was removed."),
        )

    return redirect("availability:doctor_availability")


@role_required("doctor")
def toggle_doctor_availability(request, slot_id):
    if request.method == "POST":
        slot = get_object_or_404(
            Availability,
            pk=slot_id,
            doctor=request.user,
        )

        slot.is_free = not slot.is_free
        slot.save(update_fields=["is_free"])

        messages.success(
            request,
            ui_gettext("Availability status was updated."),
        )

    return redirect("availability:doctor_availability")
