#!/usr/local/bin/python

# helper script to create resource pool IPs/hostnames
# ex usage:
# ./create_resource_pool_value_sets.py 3 200 50 10.168.90. ci-ts-

import sys

from django.core.management import setup_environ
import settings
setup_environ(settings)

from infrastructure.models import ResourcePoolValueSet
from infrastructure.models import ResourcePool

rpid = sys.argv[1]
startnum = int(sys.argv[2])
cnt = int(sys.argv[3])
ipprefix = sys.argv[4]
hostnameprefix = sys.argv[5]

rp = ResourcePool.objects.get(pk=rpid)
endnum = startnum + cnt + 1

for i in range(startnum, endnum):
    rpvs = ResourcePoolValueSet()
    rpvs.ip = "%s%s" % (ipprefix, i)
    rpvs.hostname = "%s%s" % (hostnameprefix, i)
    rpvs.save()
    print "Created RPVS for %s, %s" % (rpvs.hostname, rpvs.ip)

print
print "Successfully created %s resource pool items" % (cnt)
