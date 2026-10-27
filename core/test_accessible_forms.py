"""Rendered form associations, independent of browser/AT verification."""
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

from accounts.models import DoctorProfile
from accounts.forms import DoctorDocumentForm, DoctorSignupForm, LoginForm, SignupForm
from core.test_accessibility import Elements


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
