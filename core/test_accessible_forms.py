"""Rendered form associations, independent of browser/AT verification."""
from types import SimpleNamespace

from django import forms
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase
from django.utils.html import escape

from accounts.models import DoctorProfile
from accounts.forms import DoctorDocumentForm, DoctorSignupForm, LoginForm, SignupForm
from core.test_accessibility import Elements
from core.templatetags.accessibility import accessible_field
from medical_records.admin_forms import AdminExamenForm, AdminOrdonnanceForm
from medical_records.admin_views import AdminMedicalRecordForm
from medical_records.forms import DossierMedicalForm, ExamenForm, OrdonnanceForm
from medical_records.models import DossierMedical


def render_page(template, **context):
    user = get_user_model()(pk=1, username="example", email="example@example.com", role="admin")
    request = RequestFactory().get("/")
    request.user = user
    return render_to_string(template, {"request": request, "user": user, **context})


class AccessibleFormTests(SimpleTestCase):
    def assert_associations(self, html):
        tags = Elements(html).tags
        ids = [attrs["id"] for _, attrs in tags if attrs.get("id")]
        self.assertEqual(len(ids), len(set(ids)), "IDs must be unique")
        for _, attrs in tags:
            for attribute in ("aria-describedby", "aria-labelledby"):
                for reference in attrs.get(attribute, "").split():
                    self.assertIn(reference, ids, f"Missing description: {reference}")
        return tags

    def test_authentication_errors_are_complete_and_associated(self):
        for template, form_class in (
            ("login.html", LoginForm), ("signup.html", SignupForm),
            ("doctor/signup.html", DoctorSignupForm),
            ("doctor/upload_docs.html", DoctorDocumentForm),
        ):
            with self.subTest(template=template):
                form = form_class(data={})
                form.is_valid()
                for field in form:
                    form.add_error(field.name, f"Additional error for {field.name}")
                form.add_error(None, "First form error")
                form.add_error(None, "Second form error")
                html = render_page(f"accounts/{template}", form=form)
                tags = self.assert_associations(html)
                self.assertIn("First form error", html)
                self.assertIn("Second form error", html)
                for field in form:
                    self.assertIn(f"Additional error for {field.name}", html)
                    controls = [attrs for tag, attrs in tags if tag in ("input", "select")
                                and attrs.get("name") == field.name]
                    self.assertTrue(controls, field.name)
                    for attrs in controls:
                        self.assertEqual(attrs["aria-invalid"], "true")
                        self.assertIn(f"{field.auto_id}_error", attrs["aria-describedby"].split())
                        if attrs.get("aria-hidden") != "true":
                            self.assertTrue(any(tag == "label" and label.get("for") == attrs["id"]
                                                for tag, label in tags))

    def test_unbound_authentication_fields_are_not_marked_invalid(self):
        for template, form in (("login.html", LoginForm()), ("signup.html", SignupForm()),
                               ("doctor/signup.html", DoctorSignupForm()),
                               ("doctor/upload_docs.html", DoctorDocumentForm())):
            with self.subTest(template=template):
                tags = self.assert_associations(render_page(f"accounts/{template}", form=form))
                for tag, attrs in tags:
                    if tag in ("input", "select"):
                        self.assertNotIn("aria-invalid", attrs)

    def test_camera_feedback_has_persistent_routine_and_error_regions(self):
        for template, status_id, error_id in (
            ("accounts/login.html", "faceLoginStatus", "faceLoginError"),
            ("accounts/doctor/upload_docs.html", "status-text", "camera-error"),
            ("dashboard/profile.html", "faceEnrollStatus", "faceEnrollError"),
        ):
            with self.subTest(template=template):
                tags = self.assert_associations(render_page(template))
                by_id = {attrs["id"]: attrs for _, attrs in tags if "id" in attrs}
                self.assertEqual(by_id[status_id]["role"], "status")
                self.assertEqual(by_id[status_id]["aria-live"], "polite")
                self.assertEqual(by_id[error_id]["role"], "alert")
                self.assertEqual(by_id[error_id]["aria-atomic"], "true")
                self.assertNotIn("hidden", by_id[error_id])

    def test_authentication_autocomplete_and_password_values_are_preserved(self):
        for template, form_class in (("login.html", LoginForm), ("signup.html", SignupForm),
                                      ("doctor/signup.html", DoctorSignupForm)):
            form = form_class(data={})
            form.is_valid()
            html = render_page(f"accounts/{template}", form=form)
            for tag, attrs in Elements(html).tags:
                if tag == "input" and attrs.get("name") in form.fields:
                    expected = form.fields[attrs["name"]].widget.attrs.get("autocomplete")
                    if expected:
                        self.assertEqual(attrs.get("autocomplete"), expected)
                    if attrs.get("type") == "password":
                        self.assertNotIn("value", attrs)

    def test_administrator_review_fields_have_visible_labels_and_help(self):
        doctor = get_user_model()(pk=2, username="doctor", role="doctor")
        profile = DoctorProfile(pk=1, user=doctor, specialty="cardiology")
        html = render_page("dashboard/admin/doctor_detail.html", profile=profile)
        tags = self.assert_associations(html)
        for name in ("reviewer_note", "rejection_reason"):
            field = next(attrs for tag, attrs in tags if tag == "textarea" and attrs["name"] == name)
            label = next(attrs for tag, attrs in tags if tag == "label" and attrs.get("for") == field["id"])
            self.assertNotIn("mc-sr-only", label.get("class", ""))
            self.assertIn("aria-describedby", field)

    def test_medical_fields_resolve_help_and_all_errors_without_duplicate_ids(self):
        patient = get_user_model()(pk=2, username="patient", role="patient")
        consultation = SimpleNamespace(pk=1, appointment=SimpleNamespace(patient=patient, start=None))
        for template, form_class in (
            ("admin/form.html", AdminMedicalRecordForm),
            ("admin/prescription_form.html", AdminOrdonnanceForm),
            ("admin/examination_form.html", AdminExamenForm),
            ("my_record.html", DossierMedicalForm),
            ("prescription_form.html", OrdonnanceForm),
            ("examination_upload.html", ExamenForm),
        ):
            for bound in (False, True):
                with self.subTest(template=template, bound=bound):
                    form = form_class(data={} if bound else None, prefix="record")
                    for field in form.fields.values():
                        if isinstance(field, forms.ModelChoiceField):
                            field.queryset = field.queryset.none()
                        field.help_text = "Additional field guidance"
                    if bound:
                        form.is_valid()
                        for field in form:
                            form.add_error(field.name, f"First error for {field.name}")
                            form.add_error(field.name, f"Second error for {field.name}")
                    html = render_page(f"medical_records/{template}", form=form,
                        dossier=DossierMedical(pk=1, patient=patient), consultation=consultation)
                    tags = self.assert_associations(html)
                    for field in form:
                        widget = next(attrs for tag, attrs in tags if tag in ("input", "select", "textarea")
                                      and attrs.get("name") == field.html_name)
                        descriptions = widget["aria-describedby"].split()
                        self.assertIn(f"{field.auto_id}_helptext", descriptions)
                        if bound:
                            self.assertEqual(widget["aria-invalid"], "true")
                            self.assertIn(f"{field.auto_id}_error", descriptions)
                            self.assertIn(f"First error for {field.name}", html)
                            self.assertIn(f"Second error for {field.name}", html)
                        if template == "prescription_form.html":
                            expected = "medications-help" if field.name == "medicaments" else "instructions-help"
                            self.assertIn(expected, descriptions)

    def test_extra_descriptions_preserve_widget_attributes_and_deduplicate_tokens(self):
        class ExampleForm(forms.Form):
            notes = forms.CharField(help_text="Guidance", widget=forms.TextInput(attrs={
                "class": "existing-style", "aria-describedby": "existing-help existing-help",
            }))
        form = ExampleForm(data={}, prefix="example")
        form.is_valid()
        before = form.fields["notes"].widget.attrs.copy()
        html = accessible_field(form["notes"], "extra-help extra-help")
        widget = Elements(html).tags[0][1]
        self.assertEqual(widget["class"], "existing-style")
        self.assertEqual(widget["aria-invalid"], "true")
        self.assertEqual(widget["aria-describedby"].split(), [
            "existing-help", "id_example-notes_helptext", "id_example-notes_error", "extra-help",
        ])
        self.assertEqual(form.fields["notes"].widget.attrs, before)

    def test_locked_examination_patient_has_associated_explanation(self):
        form = AdminExamenForm()
        form.fields["dossier"].queryset = form.fields["dossier"].queryset.none()
        form.fields["dossier"].disabled = True
        tags = self.assert_associations(render_page(
            "medical_records/admin/examination_form.html", form=form))
        patient = next(attrs for tag, attrs in tags if tag == "select" and attrs.get("name") == "dossier")
        self.assertIn("disabled", patient)
        self.assertIn("examination-patient-help", patient["aria-describedby"].split())

    def test_all_password_validator_messages_are_rendered(self):
        for template, form_class in (("signup.html", SignupForm),
                                      ("doctor/signup.html", DoctorSignupForm)):
            with self.subTest(template=template):
                form = form_class(data={"email": "invalid", "password": "123",
                                        "confirm_password": "123"})
                self.assertFalse(form.is_valid())
                self.assertGreaterEqual(len(form["password"].errors), 2)
                html = render_page(f"accounts/{template}", form=form)
                self.assert_associations(html)
                for error in form["password"].errors:
                    self.assertIn(str(escape(error)), html)

    def test_login_password_errors_render_without_echoing_submitted_password(self):
        form = LoginForm(data={})
        self.assertFalse(form.is_valid())
        html = render_page("accounts/login.html", form=form)
        for error in form["password"].errors:
            self.assertIn(str(escape(error)), html)
        form = LoginForm(data={"email": "invalid", "password": "submitted-secret-example"})
        self.assertFalse(form.is_valid())
        self.assertNotIn("submitted-secret-example", render_page("accounts/login.html", form=form))

    def test_reusable_error_and_help_markup_escapes_untrusted_text(self):
        class ExampleForm(forms.Form):
            notes = forms.CharField(help_text='<script>unsafe_help()</script>')
        form = ExampleForm(data={})
        form.is_valid()
        form.add_error("notes", '<script>unsafe_error()</script>')
        html = render_to_string("components/form_field.html", {"field": form["notes"]})
        self.assert_associations(html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;unsafe_error()&lt;/script&gt;", html)
        self.assertIn("&lt;script&gt;unsafe_help()&lt;/script&gt;", html)

    def test_reusable_fields_keep_ids_unique_across_prefixed_forms(self):
        class ExampleForm(forms.Form):
            notes = forms.CharField(help_text="Guidance")
        html = ""
        for prefix in ("first", "second"):
            form = ExampleForm(data={}, prefix=prefix)
            form.is_valid()
            html += render_to_string("components/form_field.html", {"field": form["notes"]})
        tags = self.assert_associations(html)
        self.assertEqual(sum(tag == "input" for tag, _ in tags), 2)
