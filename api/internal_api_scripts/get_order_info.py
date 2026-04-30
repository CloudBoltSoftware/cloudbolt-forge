#!/usr/bin/python

# usage: <script name> <your-CloudBolt-username>

# Gets the user's current cart and prints out information about that order -
# its status, group, approvers for the group, and their email addresses

import time
import sys
import os
import sys

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
sys.path.append("..")

from django.contrib.auth.models import User, Group
from orders.models import CustomFieldValue
from orders.models import PreconfigurationValueSet
from orders.models import Order
from infrastructure.models import Server, Sector, CustomField, Preconfiguration
from accounts.models import Group, UserProfile
from externalcontent.models import OSBuild, Application

username = sys.argv[1]
user = User.objects.filter(username=username)[0]
profile = user.get_profile()
order = profile.get_current_order()

print "id, status of order:", order.id, order.status
print
print "group, sector for order:", order.group, order.sector
print
recipients = order.group.get_approvers()
print "approvers for order.group:", recipients
print
recipients = [r.user.email for r in recipients]
print "email addresses for those approvers:", recipients
print
