
"""
Core application views for the MediConnect platform.

This module handles HTTP requests related to the public-facing
pages of the application.

Each Django view processes an incoming request, prepares any
necessary data, and returns an HTTP response.
"""

from django.shortcuts import render


def home(request):
    """
    Render the public homepage of MediConnect.

    This view is responsible for displaying the main landing page
    that visitors see when accessing the platform.

    Args:
        request (HttpRequest):
            The HTTP request object provided by Django.
            It contains information about the incoming request.

    Returns:
        HttpResponse:
            The rendered homepage containing the list of
            popular medical specialties.
    """

    # Define the medical specialties highlighted on the homepage.
    #
    # These values are currently stored in a static Python list.
    # In future development, they could be retrieved dynamically
    # from the database using Django's ORM.
    popular_specialties = [
        "General Medicine",
        "Dermatology",
        "Dentistry",
        "Cardiology",
        "Pediatrics",
    ]

    # Prepare the context dictionary.
    #
    # Django uses this dictionary to transfer data from the
    # Python view to the HTML template.
    #
    # Inside the template, the specialties can be accessed
    # using the variable name "popular_specialties".
    context = {
        "popular_specialties": popular_specialties,
    }

    # Render the homepage template.
    #
    # Django loads the "core/home.html" template, combines it
    # with the context data, and returns an HTTP response
    # containing the generated HTML.
    return render(request, "core/home.html", context)
