# Standard Library
import re
from pathlib import Path
from typing import cast

# Django
from django.conf import settings
from django.template import Context, Template
from django.test import TestCase

# Wagtail
from wagtail.images.models import AbstractRendition, Image

# Third Party
from model_bakery.recipe import Recipe

# Locals
from .templatetags.picture_tags import AttrsType, get_attrs, get_media_query, get_type


class PictureTagTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        base = (Path(settings.BASE_DIR) / "..").resolve()

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
            ({"width": 100, "height": 100, "loading": "lazy"}, 'width="100" height="100" loading="lazy"'),
            ({"width": 100, "height": 100, "loading": "eager"}, 'width="100" height="100"'),
        ]
        for attrs, expected in pairs:
            self.assertEqual(get_attrs(attrs), expected)

    def test_get_attrs_eager(self):
        attrs = {
            "width": 100,
            "height": 100,
            "loading": "eager",
        }
        built_attrs = get_attrs(attrs)
        self.assertEqual(built_attrs, 'width="100" height="100"')

    def test_spec_parse(self):
        class fakeImage:
            width = self.width

        specs = (
            ("max-1000x500", "(max-width: 100px)"),
            ("height-480", "(max-width: 100px)"),
            ("scale-50", "(max-width: 100px)"),
            ("original", "(max-width: 100px)"),
            ("width-640", "(max-width: 640px)"),
            ("fill-200x200", "(max-width: 200px)"),
            ("min-500x200", "(min-width: 500px)"),
        )

        for spec, expected in specs:
            self.assertEqual(get_media_query(spec, cast(AbstractRendition, fakeImage())), expected)

    def bake_image(self, **kwargs) -> Image:
        return self.image_recipe.make(_create_files=True, **kwargs)

    def test_basic_spec(self):
        spec = f"fill-{self.width}x{self.height}"

        image = self.bake_image()
        context = Context({"image": image})
        template = Template(f"{{% load picture_tags %}}{{% picture image {spec} photo %}}")

        got = template.render(context)
        match = re.search(rf"images/mock_img(_[\w\d]+)?\.([\w\d]+)\.{spec}\.format-", got)
        self.assertIsNotNone(match)

        if match is not None:
            expected = f"""<picture>
        <source srcset="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-avif.avif" type="image/avif" width="56" height="56" />
        <source srcset="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-webp.webp" type="image/webp" width="56" height="56" />
        <source srcset="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-jpeg.jpg" type="image/jpeg" width="56" height="56" />
        <img src="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-jpeg.jpg" width="56" height="56" alt="mock" />
    </picture>"""  # noqa

            self.assertHTMLEqual(got, expected)

    def test_lazy_spec(self):
        spec = f"fill-{self.width}x{self.height}"

        image = self.bake_image()
        context = Context({"image": image})
        template = Template(f"{{% load picture_tags %}}{{% picture image {spec} photo lazy %}}")

        got = template.render(context)
        match = re.search(rf"images/mock_img(_[\w\d]+)?\.([\w\d]+)\.{spec}\.format-", got)
        self.assertIsNotNone(match)
        if match is not None:
            expected = f"""<picture>
        <source srcset="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-avif.avif" type="image/avif" width="56" height="56" loading="lazy"/>
        <source srcset="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-webp.webp" type="image/webp" width="56" height="56" loading="lazy"/>
        <source srcset="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-jpeg.jpg" type="image/jpeg" width="56" height="56" loading="lazy"/>
        <img src="/images/mock_img{match[1] or ''}.{match[2]}.{spec}.format-jpeg.jpg" width="56" height="56" alt="mock" loading="lazy"/>
    </picture>"""  # noqa

            self.assertHTMLEqual(got, expected)

    def test_size_spec(self):
        specs = [
            f"fill-{self.width//2}x{self.height//2}",
            f"fill-{self.width}x{self.height}",
            f"fill-{self.width//3}x{self.height//3}",
        ]
        spec = " ".join(specs)

        image = self.bake_image()
        context = Context({"image": image})
        template = Template(f"{{% load picture_tags %}}{{% picture image {spec} photo %}}")

        got = template.render(context)
        match = re.search(rf"images/mock_img(_[\w\d]+)?\.([\w\d]+)\.{specs[1]}\.format-", got)
        self.assertIsNotNone(match)
        if match is not None:
            expected = f"""<picture>
<source media="(max-width: 33px)" srcset="/images/mock_img{match[1] or ''}.{match[2]}.{specs[2]}.format-webp.webp" type="image/webp" width="33" height="33" />
<source media="(max-width: 33px)" srcset="/images/mock_img{match[1] or ''}.{match[2]}.{specs[2]}.format-avif.avif" type="image/avif" width="33" height="33" />
<source media="(max-width: 33px)" srcset="/images/mock_img{match[1] or ''}.{match[2]}.{specs[2]}.format-jpeg.jpg" type="image/jpeg" width="33" height="33" />
<source media="(max-width: 100px)" srcset="/images/mock_img{match[1] or ''}.{match[2]}.{specs[1]}.format-avif.avif" type="image/avif" width="56" height="56" />
<source media="(max-width: 100px)" srcset="/images/mock_img{match[1] or ''}.{match[2]}.{specs[1]}.format-webp.webp" type="image/webp" width="56" height="56" />
<source media="(max-width: 100px)" srcset="/images/mock_img{match[1] or ''}.{match[2]}.{specs[1]}.format-jpeg.jpg" type="image/jpeg" width="56" height="56" />
<source srcset="/images/mock_img{match[1] or ''}.{match[2]}.{specs[0]}.format-avif.avif" type="image/avif" width="50" height="50" />
<source srcset="/images/mock_img{match[1] or ''}.{match[2]}.{specs[0]}.format-webp.webp" type="image/webp" width="50" height="50" />
<source srcset="/images/mock_img{match[1] or ''}.{match[2]}.{specs[0]}.format-jpeg.jpg" type="image/jpeg" width="50" height="50" />
<img src="/images/mock_img{match[1] or ''}.{match[2]}.{specs[0]}.format-jpeg.jpg" width="50" height="50" alt="mock" />
</picture>
"""  # noqa

            self.assertHTMLEqual(got, expected)
