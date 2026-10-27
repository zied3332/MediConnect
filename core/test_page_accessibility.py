"""Page-level source/render checks; computed styles still need a browser."""
import re

from django.conf import settings
from django.test import SimpleTestCase


class PageAccessibilityTests(SimpleTestCase):
    def source(self, path):
        return (settings.BASE_DIR / path).read_text(encoding="utf-8")

    def declaration(self, path, selector, property):
        source = re.sub(r"/\*.*?\*/", "", self.source(path), flags=re.S)
        values = []
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", source):
            if selector in [item.strip() for item in selectors.split(",")]:
                values.extend(re.findall(rf"(?<![-\w]){re.escape(property)}:\s*([^;]+)", body))
        self.assertTrue(values, (path, selector, property))
        return values[-1].strip()

    def color(self, value):
        if value.startswith("var("):
            name = value[4:].split(",")[0].rstrip(")")
            for path in ("static/css/accessibility.css", "static/css/tokens.css",
                         "static/css/dashboard/layout.css", "static/css/dashboard/medical-records-admin.css"):
                match = re.search(rf"{re.escape(name)}:\s*(#[\da-fA-F]+)", self.source(path))
                if match:
                    return self.color(match[1])
            self.fail(f"Unknown color token: {name}")
        value = value.lstrip("#")
        return "".join(char * 2 for char in value) if len(value) == 3 else value

    def contrast(self, first, second):
        def luminance(value):
            value = self.color(value)
            channels = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            return sum((x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4) * weight
                       for x, weight in zip(channels, (.2126, .7152, .0722)))
        low, high = sorted((luminance(first), luminance(second)))
        return (high + .05) / (low + .05)

    def test_page_text_tokens_contrast_with_the_declared_light_surfaces(self):
        for color in ("var(--mc-page-muted)", "var(--mc-page-muted-gold)"):
            for background in ("#fff", "#f8f9f6", "#f7f8f4", "#f2f0e8", "#fff0be"):
                with self.subTest(color=color, background=background):
                    self.assertGreaterEqual(self.contrast(color, background), 4.5)

    def test_examination_text_contrast_on_its_declared_parent_backgrounds(self):
        css = "static/css/dashboard/medical-examinations-admin.css"
        for selector, parent in ((".mr-page .table th", ".mr-page .table thead"),
                                 (".mr-page .table .text-muted", ".mr-page .mr-card"),
                                 (".mr-page .form-text", ".mr-page .mr-card"),
                                 (".mr-page dl.row dt", ".mr-page .mr-card")):
            with self.subTest(selector=selector):
                self.assertGreaterEqual(self.contrast(self.declaration(css, selector, "color"),
                    self.declaration(css, parent, "background")), 4.5)

    def test_status_and_footer_text_contrast_on_actual_declared_backgrounds(self):
        for path, selector, parent in (
            ("static/css/doctor.css", ".mc-status-badge--pending_review", ".mc-status-badge--pending_review"),
            ("templates/accounts/login.html", ".face-login-status.error", ".face-login-status.error"),
            ("static/css/footer.css", ".mc-footer-bottom p", ".mc-footer"),
        ):
            with self.subTest(path=path, selector=selector):
                self.assertGreaterEqual(self.contrast(self.declaration(path, selector, "color"),
                    self.declaration(path, parent, "background")), 4.5)
