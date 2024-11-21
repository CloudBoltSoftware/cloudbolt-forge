#!/usr/bin/env python
"""
CloudBolt should not contain >1 CFV for the same CF with the same value.  This
script looks for cases where that loose constraint is violated.

If it prints all lines like: "[]", then the test passed.
"""
import os
os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

import django
django.setup()

from django.db.models import Count
from orders.models import CustomFieldValue

types = [
    ("DEC", "decimal"),
    ("NET", "network"),
    ("INT", "int"),
    ("STR", "str"),
    ("BOOL", "boolean"),
    ("DATE", "datetime"),
    ("LDAP", "ldap"),
    ("EMAIL", "email"),
]

for fieldtype, valtype in types:
    valtype = "{}_value".format(valtype)
    dups = CustomFieldValue.objects.filter(field__type=fieldtype).values(
        'field__name', valtype).annotate(Count('id')).order_by().filter(id__count__gt=1)
    print dups
