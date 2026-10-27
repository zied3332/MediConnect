"""Rendered contracts for the shared accessibility components."""
from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class SharedAccessibilityTests(SimpleTestCase):
    def render_shell(self, name):
        request = RequestFactory().get("/")
        request.user = get_user_model()(pk=1, username="patient", role="patient")
        return Elements(render_to_string(name, {"request": request}))

    def test_public_skip_link_is_first_link_and_has_focusable_target(self):
        self.assert_skip_contract("base.html")

    def test_dashboard_skip_link_is_first_link_and_has_focusable_target(self):
        self.assert_skip_contract("dashboard/base.html")

    def assert_skip_contract(self, template):
        tags = self.render_shell(template).tags
        first_link = next(attrs for tag, attrs in tags if tag == "a")
        self.assertEqual(first_link["href"], "#main-content")
        self.assertIn("mc-skip-link", first_link["class"].split())
        self.assertNotIn("mc-sr-only", first_link["class"].split())
        targets = [attrs for tag, attrs in tags if attrs.get("id") == "main-content"]
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["tabindex"], "-1")
        self.assertIn(("main", targets[0]), tags)
        self.assertTrue(any(tag == "link" and attrs.get("href", "").endswith(
            "/css/accessibility.css") for tag, attrs in tags))
