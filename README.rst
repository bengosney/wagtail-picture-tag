===================
Wagtail Picture Tag
===================

Wagtail Picture Tag adds a picture template tag.
It takes a the same parameters as the Wagtail Image tag but it
can accept multiple size and format parameters.

By default it will try and create JPEG, PNG, JPEG and AVIF (if available).
There are also two formate shortcuts:

- photo - will create JPEG, WEBP and AVIF
- transparent - will create WEBP, PNG and AVIF

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
