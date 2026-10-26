from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateMedicalStorage(FileSystemStorage):
    """
    Store private medical files outside the public MEDIA_ROOT.

    Files can only be accessed through authorized Django views.
    """

    def __init__(self, *args, **kwargs):
        private_root = settings.BASE_DIR / "private_medical_files"

        kwargs["location"] = private_root

        # An empty string prevents FileSystemStorage from
        # falling back to settings.MEDIA_URL.
        kwargs["base_url"] = ""

        super().__init__(*args, **kwargs)

    def url(self, name):
        """
        Never generate a public URL for a private medical file.
        """
        raise ValueError(
            "Private medical files require an authorized download view."
        )


private_medical_storage = PrivateMedicalStorage()