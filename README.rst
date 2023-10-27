===================
Wagtail Picture Tag
===================

Wagtail Picture Tag adds a picture template tag.
This is not supposed to be a solution for all situations but to be
a shortcut for most.

It accepts 3 main types of filters: formats, resizing methods and sizes.

Formats
-------
By default it will try and create JPEG, PNG, WEBP and AVIF (if available).

You may use `format-jpeg`, `format-png`, `format-webp`, `format-gif` and `format-avif`

There are also two format shortcuts:

- photo - will create JPEG, WEBP and AVIF
- transparent - will create WEBP, PNG and AVIF

Resizing
--------
Resizing methods are the same as Wagtails with the exception that you
can provide multiple filters

Sizes
-----
Sizes are automatically generated to match resizing filters provided but
can be specified for more responsive sizes.

`size-250px` will create `sizes="250px"`
`size-max100-300vw size-250px` will create `sizes="(max-width: 300px) 100vw, 250px"`

Lazy
----
It also takes the argument `lazy` that simply adds `loading="lazy"` to the HTML tag.


AVIF
----
Currently Willow (the image library used by Wagtail) does not support AVIF
but support can be patched in by installing `willowavif` package.


Quick start
-----------

1. Install the package::

    pip install wagtail-picture-tag

2. Add "wagtail-picture-tag" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'wagtail_picture_tag',
    ]

3. Include the tag in your template::

    {% load picture_tags %}

4. Use the tag::

    {% picture image photo fill-640x480 fill-320x240 %}


AVIF support
------------

All that is needed is to install the `willowavif` package, it is
then automatically imported and used.


Testing
-------
.. image:: https://circleci.com/gh/bengosney/wagtail-picture-tag/tree/main.svg?style=svg
        :target: https://circleci.com/gh/bengosney/wagtail-picture-tag/tree/main

Testing is done with pytest. Install and test can be done with::

    pip install -r requirements.txt -r requirements.dev.txt
    pytest
