"""Rendered form associations, independent of browser/AT verification."""
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

from accounts.models import DoctorProfile
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
