
from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateMedicalStorage(FileSystemStorage):
    """
    Store medical files outside the publicly served MEDIA_ROOT.
    """

    def __init__(self, *args, **kwargs):
        private_root = settings.BASE_DIR / "private_medical_files"

        super().__init__(
            location=private_root,
            base_url=None,
            *args,
            **kwargs,
        )

    def url(self, name):
        """
        Medical files must never expose a direct public URL.
        """
        raise ValueError(
            "Private medical files require an authorized download view."
        )


private_medical_storage = PrivateMedicalStorage()
