from django.shortcuts import render


def home(request):
    """Render the MediConnect public homepage."""

    popular_specialties = [
        "General Medicine",
        "Dermatology",
        "Dentistry",
        "Cardiology",
        "Pediatrics",
    ]

    context = {
        "popular_specialties": popular_specialties,
    }

    return render(request, "core/home.html", context)