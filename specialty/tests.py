from django.test import TestCase

from .forms import SpecialtyForm
from .models import Specialty


class SpecialtyModelTests(TestCase):
    def test_string_representation_uses_name(self):
        specialty = Specialty(name="Cardiology", description="Heart care")

        self.assertEqual(str(specialty), "Cardiology")

    def test_name_is_required(self):
        form = SpecialtyForm({"name": "", "description": "Heart care"})

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_duplicate_name_is_rejected(self):
        Specialty.objects.create(name="Cardiology")

        form = SpecialtyForm({"name": "Cardiology", "description": "Updated"})

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_description_is_optional(self):
        form = SpecialtyForm({"name": "Neurology", "description": ""})

        self.assertTrue(form.is_valid())
