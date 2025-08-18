#!/usr/bin/env python

import pprint
import sys
import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
sys.path.append("..")

import django

django.setup()

from jobs.models import ExternalJob

# from provisionengines.hpsa import ase_sa_common

# ts = ase_sa_common2.APIWrapper("10.168.90.42", ts_port=443, ts_user="bernard", ts_pass="opsware")
# prog = ts.get_job_progress(sys.argv[1])
# pprint.pprint(prog)

# sys.exit(0)
ej = ExternalJob.objects.get(pk=sys.argv[1])
prog = ej.get_status()
pprint.pprint(ej.prog_results)
