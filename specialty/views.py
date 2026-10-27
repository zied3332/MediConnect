from django.utils.translation import gettext_lazy as ui_gettext

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from dashboard.views import role_required

from .forms import SpecialtyForm
from .models import Specialty


@role_required("admin")
def admin_specialties(request):
    if request.method == "POST":
        form = SpecialtyForm(request.POST)

        if form.is_valid():
            specialty = form.save()

            messages.success(
                request,
                ui_gettext("%(value0)s was added.") % {"value0": specialty.name},
            )

            return redirect("specialty:admin_specialties")
    else:
        form = SpecialtyForm()

    context = {
        "page_title": ui_gettext("Specialties"),
        "dashboard_role": "admin",
        "form": form,
        "specialties": Specialty.objects.all(),
        "catalogue_specialties": Specialty.objects.all()[:4],
        "has_more_specialties": Specialty.objects.count() > 4,
        "doctors": User.objects.filter(
            role=User.Role.DOCTOR
        ).select_related("main_specialty"),
    }

    return render(
        request,
        "dashboard/admin/specialties.html",
        context,
    )


@role_required("admin")
def specialty_list(request):
    return render(
        request,
        "dashboard/admin/specialty_list.html",
        {
            "page_title": ui_gettext("Specialties"),
            "dashboard_role": "admin",
            "specialties": Specialty.objects.all(),
        },
    )


@role_required("admin")
def edit_specialty(request, specialty_id):
    specialty = get_object_or_404(
        Specialty,
        pk=specialty_id,
    )

    if request.method == "POST":
        form = SpecialtyForm(
            request.POST,
            instance=specialty,
        )

        if form.is_valid():
            form.save()
            messages.success(
                request,
                ui_gettext("%(value0)s was updated.") % {"value0": specialty.name},
            )
        else:
            messages.error(
                request,
                ui_gettext("Please correct the specialty details."),
            )

    return redirect(
        request.POST.get("next") or "specialty:specialty_list"
    )


@role_required("admin")
def delete_specialty(request, specialty_id):
    if request.method == "POST":
        specialty = get_object_or_404(
            Specialty,
            pk=specialty_id,
        )

        name = specialty.name
        specialty.delete()

        messages.success(
            request,
            ui_gettext("%(value0)s was deleted.") % {"value0": name},
        )

    return redirect(
        request.POST.get("next") or "specialty:specialty_list"
    )


@role_required("admin")
def update_doctor_specialty(request, user_id):
    if request.method != "POST":
        return redirect("specialty:admin_specialties")

    doctor = get_object_or_404(
        User,
        pk=user_id,
        role=User.Role.DOCTOR,
    )

    specialty_id = request.POST.get("specialty")

    specialty = (
        get_object_or_404(Specialty, pk=specialty_id)
        if specialty_id
        else None
    )

    doctor.main_specialty = specialty
    doctor.save(update_fields=["main_specialty"])

    messages.success(
        request,
        ui_gettext("%(value0)s's specialty was updated.")
        % {"value0": doctor.get_full_name() or doctor.email},
    )

    next_url = request.POST.get("next") or request.GET.get("next")
    return redirect(next_url or "specialty:admin_specialties")
