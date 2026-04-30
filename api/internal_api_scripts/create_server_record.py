#!/usr/bin/python

import time
import sys
import os
import sys

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from django.contrib.auth.models import User, Group
from orders.models import CustomFieldValue
from orders.models import PreconfigurationValueSet
from infrastructure.models import Server, Sector, CustomField, Preconfiguration
from accounts.models import Group, UserProfile
from externalcontent.models import OSBuild, Application

# data section ###
hpsa_mid = 5580001
hostname = "testname2"
ip = "1.2.3.4"
mac = "du:mm:y:ma:c"
project = Group.objects.filter(name="Wealth Management")[0]
sector = Sector.objects.filter(name="NYC-Dev Lab")[0]
user = User.objects.filter(username="bernard")[0]
profile = user.get_profile()
os = OSBuild.objects.filter(name="RHEL 5.5 x86_64")[0]
cfs = {"name1": "val1", "name2": "val2"}
apps = []
appnames = ["Oracle 11g", "Tomcat 7.0"]
for appname in appnames:
    app = Application.objects.get(name=appname)
    apps.append(app)
pc = Preconfiguration.objects.get(name="vm_size")
pcvs, created = PreconfigurationValueSet.objects.get_or_create(preconfiguration=pc, value="small")
# end of data section ###


# create the server
svr = Server()
svr.ip = ip
svr.hostname = hostname
svr.mac = mac
svr.owner = profile
svr.apps = apps
svr.os_build = os
svr.sector = sector
svr.group = project
svr.status = "ACTIVE"
svr.save()
print "Successfully created server record %s" % svr.id

# now that the server is created in the DB, we can add related objects
svr.preconfiguration_values.add(pcvs)

# add custom fields to the server
for cfname in cfs.keys():
    # find or create existing custom field object
    cfobj, created = CustomField.objects.get_or_create(name=cfname)
    if created:
        cfobj.label = cfname
        cfobj.save()
    # find or create existing custom field value object
    cfv, created = CustomFieldValue.objects.get_or_create(field=cfobj, value=cfs[cfname])
    svr.custom_field_values.add(cfv)

svr.save()
