#!/usr/bin/python

# usage: <script name> <CloudBolt-username>

# gets a named user's email address and prints it out

import time
import sys
import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
sys.path.append("..")

from django.contrib.auth.models import User, Group
from accounts.models import Group, UserProfile

username = sys.argv[1]
user = User.objects.filter(username=username)[0]
print user.email
