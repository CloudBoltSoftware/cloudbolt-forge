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


# gets a named user's cart and clears it.  Useful when the crt gets messed up due to a bug

from django.contrib.auth.models import User, Group
from accounts.models import Group, UserProfile

username = sys.argv[1]
user = User.objects.filter(username=username)[0]
cart = user.get_profile().get_current_order()
cart.status = "FAILED"
cart.save()
