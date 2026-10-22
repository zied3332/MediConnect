from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render

from .forms import LoginForm, SignupForm


def login_page(request):
    """GET → show login form. POST → authenticate and redirect by role."""
    if request.user.is_authenticated:
        return redirect(request.user.dashboard_url)

    form = LoginForm(request.POST or None, request=request)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        next_url = request.GET.get("next") or user.dashboard_url
        return redirect(next_url)

    return render(request, "accounts/login.html", {"form": form})


def signup_page(request):
    """GET → show signup form. POST → create patient account and log in."""
    if request.user.is_authenticated:
        return redirect(request.user.dashboard_url)

    form = SignupForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to MediConnect, {user.first_name}!")
        return redirect(user.dashboard_url)

    return render(request, "accounts/signup.html", {"form": form})


def logout_view(request):
    """Log out and redirect to home."""
    logout(request)
    return redirect("core:home")
