import django
if int(django.get_version()[0]) < 3:
    from django.contrib.staticfiles.templatetags.staticfiles import static
else:
    from django.templatetags.static import static

__all__ = ["static"]