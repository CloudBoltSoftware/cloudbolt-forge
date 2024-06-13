#!/usr/bin/env python

# generates lots of orders to try to recreate the bug
# https://cloudbolt.atlassian.net/browse/DEV-991

import os
import sys
import time

mydir = os.path.abspath(os.path.dirname(__file__))
cloudbolt_rootdir = os.path.dirname(mydir)
sys.path.insert(0, cloudbolt_rootdir)

if not "DJANGO_SETTINGS_MODULE" in os.environ:
    os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

import django
django.setup()

from c2_wrapper import create_provision_order

from infrastructure.models import Preconfiguration
from orders.models import PreconfigurationValueSet
from infrastructure.models import CustomField
from orders.models import CustomFieldValue


# gets a named user's cart and prints out the order items

from django.contrib.auth.models import User, Group
from accounts.models import Group, UserProfile


def cast_ois(order):
    for oi in order.orderitem_set.all():
        # print "#", oi.id, oi.real_type,
        oi = oi.cast()


MAX = 10000
t1 = time.time()
for i in range(0, MAX):
    cnt, order = create_provision_order(
        user="bernard", project="Bonds", environment="San Jose QA Lab",
        os_build="RHEL 5.5 x86_64", preconfig_values={"vm_size": "small", "sw_stack": "LAMP"}, quantity=1)
    if i % 50 == 0:
        print "Created order %s/%s (ID %s)" % (i + 1, MAX, order.id)
    cast_ois(order)
t2 = time.time()
t_elapsed = t2 - t1
print "Created %s orders in %s seconds" % (MAX, t_elapsed)
