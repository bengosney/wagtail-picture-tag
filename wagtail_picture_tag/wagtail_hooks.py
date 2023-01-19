from wagtail import hooks
from wagtail.images import image_operations
from wagtail.images.models import IMAGE_FORMAT_EXTENSIONS
import contextlib


#with contextlib.suppress(ImportError):
    # Third Party
import willowavif  # noqa
from willowavif import AvifPlugin  # noqa


IMAGE_FORMAT_EXTENSIONS['avif'] = '.avif'


class FormatOperation(image_operations.FormatOperation):
    def construct(self, format, *options):
        self.format = format
        self.options = options

        if self.format not in IMAGE_FORMAT_EXTENSIONS.keys():
            raise ValueError(f"Format must be one of: {', '.join(IMAGE_FORMAT_EXTENSIONS.keys())}")


@hooks.register("register_image_operations", order=1)
def register_image_operations():
    return [
        ("format", FormatOperation),
    ]
