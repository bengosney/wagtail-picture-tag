# Standard Library
import contextlib
import hashlib
import os
import re
from collections import defaultdict
from collections.abc import Mapping
from functools import cached_property, lru_cache
from io import BytesIO
from typing import Literal

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

try:
    # Third Party
    import willowavif  # noqa
except ImportError as e:
    if e.name != "willowavif":
        raise e

AttrsType = Mapping[str, object]

register = template.Library()

size_regex = re.compile(r"^size-(((?P<mod>min|max)(?P<width>\d+))-)?(?P<size>\d+(px|vw))$")


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
            avifRendition = _get_avif_renditions_fallback(image_rendition, image, avifSpec, cache_key)
    return avifRendition


def _get_avif_renditions_fallback(image_rendition, image, avifSpec, cache_key):
    with image_rendition.get_willow_image() as willow:
        avifImage = willow.save_as_avif(BytesIO())

    input_filename_without_extension, _ = os.path.splitext(image.filename)
    output_extension = avifSpec.replace("|", ".") + ".avif"
    if cache_key:
        output_extension = f"{cache_key}.{output_extension}"
    output_filename_without_extension = input_filename_without_extension[: (59 - len(output_extension))]
    output_filename = f"{output_filename_without_extension}.{output_extension}"

    result, _ = image.renditions.get_or_create(
        filter_spec=avifSpec,
        focal_point_key=cache_key,
        defaults={"file": File(avifImage.f, name=output_filename)},
    )
    return result


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

    with contextlib.suppress(FileNotFoundError):
        renditions.sort(key=lambda r: r.file.size)

    return renditions


@lru_cache
def parse_size(raw_str: str) -> str:
    size = "100vw"
    if match := size_regex.match(raw_str):
        groups = match.groupdict()
        size = str(groups["size"])
        if groups["mod"] is not None and groups["width"] is not None:
            size = f"({groups['mod']}-width: {groups['width']}px) {size}"

    return size


@register.tag()
def picture(parser, token):
    bits = token.split_contents()[1:]
    image_expr = parser.compile_filter(bits[0])

    filter_specs: list[str] = []
    formats: list[str] = []
    loading: Literal["eager"] | Literal["lazy"] = "eager"
    size_specs: list[str] = []
    for spec in bits[1:]:
        if spec == "transparent":
            formats += ["png", "webp", "avif"]
        elif spec == "photo":
            formats += ["jpeg", "webp", "avif"]
        elif spec.startswith("format-"):
            formats.append(spec.split("-")[1])
        elif spec.startswith("size-"):
            size_specs.append(spec)
        elif spec == "lazy":
            loading = "lazy"
        else:
            filter_specs.append(spec)

    if not formats:
        formats = ["webp", "jpeg", "png", "avif"]

    return PictureNode(image_expr, filter_specs, list(set(formats)), loading, size_specs)


def get_attrs(attrs: AttrsType) -> str:
    return " ".join(f'{k}="{v}"' for k, v in attrs.items() if v != "eager" or k != "loading")


@lru_cache
def get_type(ext: str) -> str:
    ext = ext.lower().strip(".")
    type_ = "jpeg" if ext == "jpg" else ext
    return f"image/{type_}"


@lru_cache
def build_media_query(sizes: tuple[int]) -> str:
    media_queries: list[str] = []
    prev: int | None = None
    for size in sizes[:-1]:
        if prev is None:
            media_queries.append(f"(max-width: {size}px) {size}px")
        else:
            media_queries.append(f"(min-width: {prev}px) and (max-width: {size}px) {size}px")
        prev = size

    media_queries.append(f"{sizes[-1]}px")

    return ", ".join(media_queries)


class PictureNode(template.Node):
    def __init__(self, image: FilterExpression, specs: list[str], formats: list[str], loading: str, sizes: list[str]) -> None:
        self.image = image
        self.specs = specs
        self.formats = formats
        self.loading = loading
        self.sizes = sizes

        super().__init__()

    @cached_property
    def has_sizes(self):
        return len(self.sizes) > 0

    def render(self, context: Context) -> str:
        if (image := self.image.resolve(context)) is None:  # type: ignore
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

        image_srcs: dict[str, list[str]] = defaultdict(list)
        image_sizes: set[int] = set()
        base = None
        for spec in self.specs:
            renditions = get_renditions(image, spec, self.formats)
            for rendition in renditions:
                _, extension = os.path.splitext(rendition.file.name)
                image_srcs[get_type(extension)].append(f"{rendition.url} {rendition.width}w")
                image_sizes.add(rendition.width)
                base = base or rendition

        if base is None:
            return ""

        srcsets: list[str] = []
        for file_type, srcset in image_srcs.items():
            attrs = {
                "srcset": ", ".join(srcset),
                "type": file_type,
                "sizes": ", ".join(parse_size(s) for s in self.sizes)
                if self.has_sizes
                else build_media_query(tuple(sorted(image_sizes))),
            }
            srcsets.append(f"<source {get_attrs(attrs)} />")

        attrs = {
            "src": base.url,
            "alt": base.alt,
            "width": base.width,
            "height": base.height,
            "loading": self.loading,
        }

        picture = f"""<picture>
    {"".join(srcsets)}
    <img {get_attrs(attrs)} />
</picture>"""

        if cache_key and cache:
            cache.set(cache_key, picture)

        return mark_safe(picture)
