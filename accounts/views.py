from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .forms import DoctorDocumentForm, DoctorSignupForm, LoginForm, SignupForm
from .models import DoctorProfile
from .tokens import email_confirmation_token

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _send_confirmation_email(request, user):
    """Send the email-confirmation link to a newly registered doctor."""
    from django.conf import settings

    uid   = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_confirmation_token.make_token(user)
    link  = request.build_absolute_uri(
        f"/accounts/doctor/confirm-email/{uid}/{token}/"
    )
    send_mail(
        subject="MediConnect — Confirm your email address",
        message=(
            f"Hi Dr. {user.first_name},\n\n"
            "Please confirm your email address by clicking the link below:\n\n"
            f"{link}\n\n"
            "This link expires in 3 days.\n\n"
            "— The MediConnect team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Patient login / signup / logout
# ─────────────────────────────────────────────────────────────────────────────

def login_page(request):
    """
    Unified login for all roles.

    Doctors with non-approved status are redirected to the
    appropriate status page rather than their dashboard.
    """
    if request.user.is_authenticated:
        return _post_login_redirect(request.user)

    form = LoginForm(request.POST or None, request=request)

    if request.method == "POST":
        # Special handling: catch inactive doctor accounts so we can show a
        # meaningful status page instead of "account is inactive".
        raw_email = request.POST.get("email", "").lower().strip()
        try:
            candidate = User.objects.get(email=raw_email)
        except User.DoesNotExist:
            candidate = None

        if (
            candidate
            and candidate.role == User.Role.DOCTOR
            and not candidate.is_active
            and candidate.check_password(request.POST.get("password", ""))
        ):
            # Correct credentials but account not yet active — show status.
            try:
                profile = candidate.doctor_profile
            except DoctorProfile.DoesNotExist:
                profile = None

            if profile and profile.status == DoctorProfile.Status.PENDING_DOCUMENTS:
                return redirect("accounts:doctor_upload_docs", pk=candidate.pk)

            # pending_review / needs_more_info / rejected — show status page
            return render(request, "accounts/doctor/status.html", {
                "profile": profile,
                "user": candidate,
            })

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get("next") or None
            if next_url:
                return redirect(next_url)
            return _post_login_redirect(user)

    return render(request, "accounts/login.html", {"form": form})


def _post_login_redirect(user):
    """
    Redirect a successfully authenticated user.
    Approved doctors → dashboard, others → status page.
    """
    if user.role == User.Role.DOCTOR:
        try:
            profile = user.doctor_profile
        except DoctorProfile.DoesNotExist:
            return redirect("core:home")
        if not profile.can_access_dashboard:
            return redirect("accounts:doctor_status")
    return redirect(user.dashboard_url)


def signup_page(request):
    """Patient signup."""
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
    logout(request)
    return redirect("core:home")


# ─────────────────────────────────────────────────────────────────────────────
# Doctor registration flow
# ─────────────────────────────────────────────────────────────────────────────

def doctor_signup(request):
    """
    Step 1 — Doctor enters email, name, specialty, password.
    Account created (inactive). Confirmation email sent.
    """
    if request.user.is_authenticated:
        return redirect(request.user.dashboard_url)

    form = DoctorSignupForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        _send_confirmation_email(request, user)
        return render(request, "accounts/doctor/check_email.html", {"email": user.email})

    return render(request, "accounts/doctor/signup.html", {"form": form})


def doctor_confirm_email(request, uidb64, token):
    """
    Step 2 — User clicks the link in their email.
    Activates the account and redirects to document upload.
    """
    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not email_confirmation_token.check_token(user, token):
        return render(request, "accounts/doctor/confirm_invalid.html", status=400)

    # Activate the account.
    user.is_active = True
    user.save(update_fields=["is_active"])

    # Log the user in so they land directly on the upload page.
    login(request, user)

    return redirect("accounts:doctor_upload_docs", pk=user.pk)


@login_required(login_url="accounts:login")
def doctor_upload_docs(request, pk):
    """
    Step 3 — Doctor uploads their verification documents.
    Only accessible by the owner of that profile.
    """
    user = get_object_or_404(User, pk=pk, role=User.Role.DOCTOR)

    # Only the owner can upload their own docs.
    if request.user != user:
        return redirect("accounts:doctor_status")

    profile = get_object_or_404(DoctorProfile, user=user)

    # If already submitted or approved, redirect to status.
    if profile.status not in (
        DoctorProfile.Status.PENDING_DOCUMENTS,
        DoctorProfile.Status.NEEDS_MORE_INFO,
    ):
        return redirect("accounts:doctor_status")

    form = DoctorDocumentForm(
        request.POST or None,
        request.FILES or None,
        instance=profile,
    )

    if request.method == "POST" and form.is_valid():
        profile = form.save(commit=False)
        profile.status = DoctorProfile.Status.PENDING_REVIEW
        profile.submitted_at = timezone.now()
        profile.save()
        return redirect("accounts:doctor_status")

    return render(request, "accounts/doctor/upload_docs.html", {
        "form": form,
        "profile": profile,
        "is_resubmit": profile.status == DoctorProfile.Status.NEEDS_MORE_INFO,
        "reviewer_note": profile.reviewer_note,
    })


@login_required(login_url="accounts:login")
def doctor_status(request):
    """
    Status page shown to doctors who are not yet approved.
    Approved doctors are redirected straight to their dashboard.
    """
    user = request.user

    if user.role != User.Role.DOCTOR:
        return redirect(user.dashboard_url)

    try:
        profile = user.doctor_profile
    except DoctorProfile.DoesNotExist:
        return redirect("core:home")

    if profile.can_access_dashboard:
        return redirect("dashboard:doctor_overview")

    return render(request, "accounts/doctor/status.html", {
        "profile": profile,
        "user": user,
    })
