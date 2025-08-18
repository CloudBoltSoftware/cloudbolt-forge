#!/usr/bin/python

import sys

from provisionengines.hpsa.models import HPSACore

c = HPSACore.objects.all()[0]
print c.get_job_results(sys.argv[1])
