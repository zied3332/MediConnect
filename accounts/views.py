
from django.shortcuts import render


def login_page(request):
    """Display the MediConnect login interface."""
    return render(request, "accounts/login.html")


def signup_page(request):
    """Display the MediConnect registration interface."""
    return render(request, "accounts/signup.html")
