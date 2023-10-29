# Standard Library
import contextlib
import re
from pathlib import Path

# Django
from django.conf import settings
from django.template import Context, Template
from django.test import TestCase

# Wagtail
from wagtail.images.models import Image

# Third Party
from model_bakery import baker
from model_bakery.random_gen import gen_image_field
from model_bakery.recipe import Recipe

# Locals
from .templatetags.picture_tags import AttrsType, get_attrs, get_type, parse_size

try:
    # Third Party
    import willowavif  # noqa
except ImportError as e:
    if e.name != "willowavif":
        raise e


class PictureTagTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        base = (Path(settings.BASE_DIR) / "..").resolve()

        with contextlib.suppress(FileNotFoundError):
            for dir in ["images", "original_images"]:
                path = base / dir
                for f in path.glob("*"):
                    f.unlink()
                Path.rmdir(path)

        super().tearDownClass()

    def setUp(self) -> None:
        self.width: int = 100
        self.height: int = 100
        self.image_recipe: Recipe[Image] = Recipe(Image, title="mock", width=self.width, height=self.height, _create_files=True)
        with contextlib.suppress(AttributeError):
            baker.generators.add("wagtail.images.models.WagtailImageField", gen_image_field)
        self.maxDiff = 1000

        return super().setUp()

    def test_get_type(self):
        types = [
            (".jpg", "image/jpeg"),
            (".jpeg", "image/jpeg"),
            (".png", "image/png"),
            (".webp", "image/webp"),
            (".avif", "image/avif"),
        ]
        for ext, type in types:
            self.assertEqual(get_type(ext), type)

    def test_get_attrs(self):
        pairs: list[tuple[AttrsType, str]] = [
            (
                {"width": 100, "height": 100, "loading": "lazy"},
                'width="100" height="100" loading="lazy"',
            ),
            (
                {"width": 100, "height": 100, "loading": "eager"},
                'width="100" height="100"',
            ),
        ]
        for attrs, expected in pairs:
            self.assertEqual(get_attrs(attrs), expected)

    def test_parse_size_empty_string(self):
        """Empty string should return 100vw."""
        self.assertEqual(parse_size(""), "100vw")

    def test_parse_size_matches_vw(self):
        self.assertEqual(parse_size("size-25vw"), "25vw")

    def test_parse_size_matches_px(self):
        self.assertEqual(parse_size("size-25px"), "25px")

    def test_parse_size_matches_min(self):
        self.assertEqual(parse_size("size-min100-25px"), "(min-width: 100px) 25px")

    def test_parse_size_matches_max(self):
        self.assertEqual(parse_size("size-max100-25px"), "(max-width: 100px) 25px")

    def bake_image(self, **kwargs) -> Image:
        return self.image_recipe.make(_create_files=True, **kwargs)

    def test_basic_spec(self):
        spec = f"fill-{self.width}x{self.height}"

        image = self.bake_image()
        rendition = image.get_rendition(spec)
        context = Context({"image": image})
        template = Template(
            f"{{% load picture_tags %}}{{% picture image {spec} photo %}}",
        )

        got = template.render(context)
        match = re.search(
            rf"images/mock_img(_[\w\d]+)?\.([\w\d]+)\.{spec}\.format-",
            got,
        )
        self.assertIsNotNone(match)

        if match is not None:
            expected = f"""<picture>
  <source srcset="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-avif.avif {rendition.width}w" type="image/avif" sizes="{rendition.width}px" />
  <source srcset="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-webp.webp {rendition.width}w" type="image/webp" sizes="{rendition.width}px" />
  <source srcset="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-jpeg.jpg {rendition.width}w" type="image/jpeg" sizes="{rendition.width}px" />
  <img src="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-avif.avif" alt="mock" width="{rendition.width}" height="{rendition.height}" />
</picture>"""  # noqa

            self.assertHTMLEqual(got, expected)

    def test_lazy_spec(self):
        spec = f"fill-{self.width}x{self.height}"

        image = self.bake_image()
        rendition = image.get_rendition(spec)
        context = Context({"image": image})
        template = Template(f"{{% load picture_tags %}}{{% picture image {spec} photo lazy %}}")

        got = template.render(context)
        match = re.search(rf"images/mock_img(_[\w\d]+)?\.([\w\d]+)\.{spec}\.format-", got)
        self.assertIsNotNone(match)
        if match is not None:
            expected = f"""<picture>
  <source srcset="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-avif.avif {rendition.width}w" type="image/avif" sizes="{rendition.width}px" />
  <source srcset="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-webp.webp {rendition.width}w" type="image/webp" sizes="{rendition.width}px" />
  <source srcset="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-jpeg.jpg {rendition.width}w" type="image/jpeg" sizes="{rendition.width}px" />
  <img src="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-avif.avif" alt="mock" width="{rendition.width}" height="{rendition.height}" loading="lazy" />
</picture>"""  # noqa

            self.assertHTMLEqual(got, expected)

    def test_size_spec(self):
        specs = [
            f"fill-{self.width//3}x{self.height//3}",
            f"fill-{self.width//2}x{self.height//2}",
            f"fill-{self.width}x{self.height}",
        ]
        spec = " ".join(specs)

        image = self.bake_image()
        renditions = [image.get_rendition(s) for s in specs]
        context = Context({"image": image})
        template = Template(f"{{% load picture_tags %}}{{% picture image {spec} photo %}}")

        self.maxDiff = 2723 * 2
        got = template.render(context)
        match = re.search(
            rf"images/mock_img(_[\w\d]+)?\.([\w\d]+)\.{specs[1]}\.format-",
            got,
        )
        self.assertIsNotNone(match)
        if match is not None:
            expected = f"""<picture>
  <source
    srcset="/images/mock_img{match[1] or ''}.{match[2]}.{specs[0]}.format-webp.webp {renditions[0].width}w, /images/mock_img{match[1] or ''}.{match[2]}.{specs[1]}.format-webp.webp {renditions[1].width}w, /images/mock_img{match[1] or ''}.{match[2]}.{specs[2]}.format-webp.webp {renditions[2].width}w"
    type="image/webp"
    sizes="(max-width: {renditions[0].width}px) {renditions[0].width}px, (min-width: {renditions[0].width}px) and (max-width: {renditions[1].width}px) {renditions[1].width}px, {renditions[2].width}px"
  />
  <source
    srcset="/images/mock_img{match[1] or ''}.{match[2]}.{specs[0]}.format-avif.avif {renditions[0].width}w, /images/mock_img{match[1] or ''}.{match[2]}.{specs[1]}.format-avif.avif {renditions[1].width}w, /images/mock_img{match[1] or ''}.{match[2]}.{specs[2]}.format-avif.avif {renditions[2].width}w"
    type="image/avif"
    sizes="(max-width: {renditions[0].width}px) {renditions[0].width}px, (min-width: {renditions[0].width}px) and (max-width: {renditions[1].width}px) {renditions[1].width}px, {renditions[2].width}px"
  />
  <source
    srcset="/images/mock_img{match[1] or ''}.{match[2]}.{specs[0]}.format-jpeg.jpg {renditions[0].width}w, /images/mock_img{match[1] or ''}.{match[2]}.{specs[1]}.format-jpeg.jpg {renditions[1].width}w, /images/mock_img{match[1] or ''}.{match[2]}.{specs[2]}.format-jpeg.jpg {renditions[2].width}w"
    type="image/jpeg"
    sizes="(max-width: {renditions[0].width}px) {renditions[0].width}px, (min-width: {renditions[0].width}px) and (max-width: {renditions[1].width}px) {renditions[1].width}px, {renditions[2].width}px"
  />
  <img
    src="/images/mock_img{match[1] or ''}.{match[2]}.{specs[0]}.format-webp.webp"
    width="{renditions[0].width}"
    height="{renditions[0].height}"
    alt="mock"
  />
</picture>"""  # noqa

            self.assertHTMLEqual(got, expected)
