from wagtail import hooks
from wagtail.images import image_operations


class FormatOperation(image_operations.FormatOperation):
    def construct(self, format, *options):
        self.format = format
        self.options = options

        if self.format not in ["jpeg", "png", "gif", "webp", "avif"]:
            raise ValueError("Format must be either 'jpeg', 'png', 'gif', 'webp' or 'avif'")


@hooks.register("register_image_operations")
def register_image_operations():
    return [
        ("format", FormatOperation),
    ]
