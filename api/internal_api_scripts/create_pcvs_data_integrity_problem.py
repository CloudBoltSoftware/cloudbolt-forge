#!/usr/bin/env python

import os
import sys

mydir = os.path.abspath(os.path.dirname(__file__))
cloudbolt_rootdir = os.path.dirname(mydir)
sys.path.insert(0, cloudbolt_rootdir)

if not "DJANGO_SETTINGS_MODULE" in os.environ:
    os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

import django
django.setup()

from infrastructure.models import Preconfiguration
from orders.models import PreconfigurationValueSet
from infrastructure.models import CustomField
from orders.models import CustomFieldValue

cf = CustomField.objects.get(name="mem_size")
pcvs = PreconfigurationValueSet.objects.get(value="small")
cfvs, created = CustomFieldValue.objects.get_or_create(field=cf, value=8)
# note: after bug #543 is resolved, the following statement should throw an
# exception (preferably a DataIntegrityException, which needs to be defined in
# utilities.exceptions)
pcvs.custom_field_values.add(cfvs)

# note: this print statement will show 2 memory CFVSes that are attached to the
# PCVS
print pcvs.custom_field_values.filter(field=cf)
