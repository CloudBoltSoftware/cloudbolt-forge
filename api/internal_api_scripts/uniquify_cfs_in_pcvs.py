#!/usr/local/bin/python

# Bernard Sanders 2/14/2012
# should be run from CloudBolt 'src' directory

import time
import sys
import os
import sys

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
sys.path.append("..")

from orders.models import PreconfigurationValueSet


def uniquify_pcv(pcv):
    used_cfs = []
    for cfv in pcv.custom_field_values.all():
        cf = cfv.field
        if cf in used_cfs:
            pcv.custom_field_values.remove(cfv)
        else:
            used_cfs.append(cf)
    pcv.save()


if __name__ == "__main__":
    for pcv in PreconfigurationValueSet.objects.all():
        uniquify_pcv(pcv)
