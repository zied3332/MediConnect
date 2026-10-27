from django.utils.translation import gettext_lazy as ui_gettext
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
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
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
        # Specify backend explicitly since we have multiple backends
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, ui_gettext('Welcome to MediConnect, %(value0)s!') % {'value0': user.first_name})
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
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

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


# ─────────────────────────────────────────────────────────────────────────────
# Face Login API endpoints
# ─────────────────────────────────────────────────────────────────────────────

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json


@require_http_methods(["GET"])
def get_face_descriptors(request):
    """
    Return all face descriptors for face matching in browser.
    
    Returns: {
        "descriptors": [
            {"user_id": 1, "descriptor": [0.1, 0.2, ...], "name": "John Doe"},
            ...
        ]
    }
    """
    users_with_faces = User.objects.filter(
        face_descriptor__isnull=False
    ).exclude(face_descriptor="")
    
    descriptors = []
    for user in users_with_faces:
        try:
            descriptor_data = json.loads(user.face_descriptor)
            descriptors.append({
                "user_id": user.id,
                "descriptor": descriptor_data,
                "name": user.get_full_name(),
            })
        except (json.JSONDecodeError, ValueError):
            continue
    
    return JsonResponse({"descriptors": descriptors})


@csrf_exempt
@require_http_methods(["POST"])
def face_login(request):
    """
    Verify face match and log in user.
    
    Expected POST data:
    {
        "user_id": 123
    }
    
    The frontend has already matched the face - server just verifies
    the user exists and has face login enabled.
    """
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        
        if not user_id:
            return JsonResponse({"success": False, "error": ui_gettext("User ID required")}, status=400)
        
        user = User.objects.get(id=user_id, is_active=True)
        
        # Verify user has face descriptor set up
        if not user.face_descriptor:
            return JsonResponse({"success": False, "error": ui_gettext("Face login not set up")}, status=400)
        
        # Log the user in
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        
        return JsonResponse({
            "success": True,
            "redirect_url": user.dashboard_url
        })
        
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": ui_gettext("User not found")}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": ui_gettext("Invalid JSON")}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def enroll_face(request):
    """
    Save face descriptor for current user.
    
    Expected POST data:
    {
        "descriptor": [0.1, 0.2, 0.3, ...],  // 128-dimensional array
        "image_data": "data:image/jpeg;base64,..."  // base64 image
    }
    """
    try:
        data = json.loads(request.body)
        descriptor = data.get("descriptor")
        image_data = data.get("image_data")
        
        if not descriptor:
            return JsonResponse({"success": False, "error": ui_gettext("Descriptor required")}, status=400)
        
        # Validate descriptor is an array of 128 numbers
        if not isinstance(descriptor, list) or len(descriptor) != 128:
            return JsonResponse({
                "success": False,
                "error": ui_gettext("Descriptor must be array of 128 numbers")
            }, status=400)
        
        # Save descriptor as JSON
        request.user.face_descriptor = json.dumps(descriptor)
        
        # Optionally save profile picture from base64
        if image_data and image_data.startswith("data:image"):
            from django.core.files.base import ContentFile
            import base64
            
            # Extract base64 data
            format_str, img_str = image_data.split(';base64,')
            ext = format_str.split('/')[-1]
            
            # Decode and save
            image_content = ContentFile(
                base64.b64decode(img_str),
                name=f"user_{request.user.id}_face.{ext}"
            )
            request.user.profile_picture.save(
                f"user_{request.user.id}_face.{ext}",
                image_content,
                save=False
            )
        
        request.user.save()
        
        return JsonResponse({"success": True, "message": ui_gettext("Face enrolled successfully")})
        
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": ui_gettext("Invalid JSON")}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
