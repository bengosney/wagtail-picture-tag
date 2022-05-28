# Standard Library
import contextlib
import hashlib
import os
import re
from io import BytesIO
from typing import Mapping

# Django
from django import template
from django.core.cache import InvalidCacheBackendError, caches
from django.core.files import File
from django.template import Context
from django.template.base import FilterExpression
from django.utils.safestring import mark_safe

# Wagtail
from wagtail.images.exceptions import InvalidFilterSpecError
from wagtail.images.models import AbstractImage, AbstractRendition, Filter, Rendition

with contextlib.suppress(ImportError):
    # Third Party
    import willowavif  # noqa

AttrsType = Mapping[str, object]

register = template.Library()

spec_regex = re.compile(r"^(?P<op>\w+)((-(?P<size>\d+))(x(\d+))?)?$")


def parse_spec(spec: str) -> tuple[str | None, int]:
    """Parse a filter specification."""
    if not (match := spec_regex.match(spec)):
        return None, 0
    groups = match.groupdict()

    try:
        return f"{groups['op']}", int(groups["size"])
    except (ValueError, TypeError):
        return f"{groups['op']}", 0


def get_media_query(spec: str, image: AbstractRendition) -> str:
    """Get a media query for the given filter specification."""
    mediaquery = ""
    op, size = parse_spec(spec)

    if op in ["fill", "width"]:
        mediaquery = f"(max-width: {size}px)"
    elif op in ["max", "height", "scale", "original"]:
        mediaquery = f"(max-width: {image.width}px)"
    elif op in ["min"]:
        mediaquery = f"(min-width: {size}px)"

    return mediaquery


def get_avif_rendition(image: AbstractImage, image_rendition: AbstractRendition, filter_spec: str) -> AbstractRendition:
    avifSpec = "|".join([filter_spec, "format-avif"])
    filter_ = Filter(spec=filter_spec)
    cache_key = filter_.get_cache_key(image)

    try:
        avifRendition = image.get_rendition(avifSpec)
    except InvalidFilterSpecError:
        try:
            avifRendition = image.renditions.get(
                filter_spec=avifSpec,
                focal_point_key=cache_key,
            )
        except Rendition.DoesNotExist:
            with image_rendition.get_willow_image() as willow:
                avifImage = willow.save_as_avif(BytesIO())

            input_filename_without_extension, _ = os.path.splitext(image.filename)
            output_extension = avifSpec.replace("|", ".") + ".avif"
            if cache_key:
                output_extension = f"{cache_key}.{output_extension}"
            output_filename_without_extension = input_filename_without_extension[: (59 - len(output_extension))]
            output_filename = f"{output_filename_without_extension}.{output_extension}"

            avifRendition, _ = image.renditions.get_or_create(
                filter_spec=avifSpec, focal_point_key=cache_key, defaults={"file": File(avifImage.f, name=output_filename)}
            )
    return avifRendition


def get_renditions(image: AbstractImage, filter_spec: str, formats: list[str]) -> list[AbstractRendition]:
    """Get a list of renditions that match the filter specification."""
    if not filter_spec:
        return []

    try:
        _ = Filter(spec=filter_spec)
    except InvalidFilterSpecError:
        return []

    formats.sort(reverse=True)
    renditions = [image.get_rendition("|".join([filter_spec, f"format-{f}"])) for f in formats if f != "avif"]

    if "avif" in formats:
        with contextlib.suppress(AttributeError):
            renditions.append(get_avif_rendition(image, renditions[0], filter_spec))

    renditions.sort(key=lambda r: r.file.size)

    return renditions


@register.tag()
def picture(parser, token):
    bits = token.split_contents()[1:]
    image_expr = parser.compile_filter(bits[0])

    filter_specs = []
    formats = []
    loading = "eager"
    for spec in bits[1:]:
        if spec == "transparent":
            formats += ["png", "webp", "avif"]
        elif spec == "photo":
            formats += ["jpeg", "webp", "avif"]
        elif spec.startswith("format-"):
            formats.append(spec.split("-")[1])
        elif spec == "lazy":
            loading = "lazy"
        else:
            filter_specs.append(spec)

    if not formats:
        formats = ["webp", "jpeg", "png", "avif"]

    return PictureNode(image_expr, filter_specs, list(set(formats)), loading)


def get_attrs(attrs: AttrsType) -> str:
    return " ".join(f'{k}="{v}"' for k, v in attrs.items() if v != "eager" or k != "loading")


def get_type(ext: str) -> str:
    ext = ext.lower().strip(".")
    type_ = "jpeg" if ext == "jpg" else ext
    return f"image/{type_}"


def get_source(rendition: AbstractRendition, **kwargs) -> str:
    _, extension = os.path.splitext(rendition.file.name)

    attrs = {
        "srcset": rendition.url,
        "type": get_type(extension),
        "width": rendition.width,
        "height": rendition.height,
    } | kwargs

    return f"<source {get_attrs(attrs)} />"


class PictureNode(template.Node):
    def __init__(self, image: FilterExpression, specs: list[str], formats: list[str], loading: str) -> None:
        self.image = image
        self.specs = specs
        self.formats = formats
        self.loading = loading

        super().__init__()

    def render(self, context: Context) -> str:
        if (image := self.image.resolve(context)) is None:
            return ""

        try:
            cache_keys: list[str] = []
            for spec in self.specs:
                f: Filter = Filter(spec=spec)
                cache_keys.extend((f.get_cache_key(image), spec))
            cache_keys.append(image.file_hash)

            cache_key: str | None = hashlib.sha1("|".join(set(cache_keys)).encode("utf-8")).hexdigest()

            cache = caches["renditions"]
            if cached_picture := cache.get(cache_key):
                return mark_safe(cached_picture)
        except InvalidCacheBackendError:
            cache_key = None
            cache = None

        baseSpec: str = self.specs[0]
        sizedSpecs: list[str] = self.specs[1:]
        base = None

        srcsets: list[str] = []
        sizedSpecs.sort(key=lambda spec: parse_spec(spec)[1])
        for spec in sizedSpecs:
            renditions = get_renditions(image, spec, self.formats)
            for rendition in renditions:
                attrs = {
                    "loading": self.loading,
                    "media": get_media_query(spec, rendition),
                }
                srcsets.append(get_source(rendition, **attrs))

        renditions = get_renditions(image, baseSpec, self.formats)
        for rendition in renditions:
            _, extension = os.path.splitext(rendition.file.name)
            srcsets.append(get_source(rendition, loading=self.loading))

            if base is None and extension in [".jpg", ".png"]:
                base = rendition

        if base is None:
            base = renditions.pop()

        attrs = {
            "src": base.url,
            "width": base.width,
            "height": base.height,
            "alt": base.alt,
            "loading": self.loading,
        }

        picture = f"""<picture>
    {"".join(srcsets)}
    <img {get_attrs(attrs)} />
</picture>"""

        if cache_key and cache:
            cache.set(cache_key, picture)

        return mark_safe(picture)
