#!/usr/bin/env python
# Author: Steven Manross
# Partner: Riverturn, Inc
# Created: 3/15/2018
#
# Tested using: Cloudbolt 7.72
#
# Description: 
#             Set the enable_monitoring, monitoring_group, and monitoring_tool as Service Parameters on a newly built server
#
# Requires: 
#             *Cloudbolt Parameters: enable_mointoring (boolean), monitoring_tool (string), monitoring_group (string)

from common.methods import set_progress
from infrastructure.models import CustomField
from orders.models import CustomFieldValue


def run(job, service, **kwargs):

    osbuildname = ""

    bpc = kwargs.get('blueprint_context')
    
    #  dynamically look up the Server Tier name (this doesn't deal with multiple server tiers...  sorry)
    for keyname in bpc.keys():
        if bpc[keyname] != "{}" and type(bpc[keyname]) is dict:
            if "os_build" in bpc[keyname].keys():
                osbuildname = keyname
                break

    if osbuildname == "" :
        return "FAILURE", "PLUGIN ERROR", "Exiting prematurely from plugin.  No os_build found!"
    else:
        set_progress("OS-BUILD-NAME: {}".format(osbuildname))
    
    mon_tool = kwargs.get('blueprint_context')[osbuildname]['monitoring_tool']
    set_progress('MON_TOOL: {}'.format(mon_tool))

    mon_group = kwargs.get('blueprint_context')[osbuildname]['monitoring_group']
    set_progress('MON_GROUP: {}'.format(mon_group))

    enable_mon = kwargs.get('blueprint_context')[osbuildname]['enable_monitoring']
    set_progress('ENABLE_MON: {}'.format(enable_mon))

    param_count = 0
    
    if enable_mon != "None":
        param_count += 1
        set_progress("Setting service parameter: {} - {} - {}".format("enable_monitoring", "Enable Monitoring", enable_mon))
        cf, _ = CustomField.objects.get_or_create(name="enable_monitoring", label="Enable Monitoring",type='BOOL')
        service.update_cf_value(cf, enable_mon, job.owner)

    if mon_tool != "None":
        param_count += 1
        set_progress("Setting service parameter: {} - {} - {}".format("monitoring_tool", "Monitoring Tool", mon_tool))
        cf, _ = CustomField.objects.get_or_create(name="monitoring_tool", label="Monitoring Tool",type='STR')
        service.update_cf_value(cf, mon_tool, job.owner)

    if mon_group != "None":
        param_count += 1
        set_progress("Setting service parameter: {} - {} - {}".format("monitoring_group", "Monitoring Group", mon_group))
        cf, _ = CustomField.objects.get_or_create(name="monitoring_group", label="Monitoring Group",type='STR')
        service.update_cf_value(cf, mon_group, job.owner)

    if param_count == 3:
        #only succeed if you set all 3 parameters
        return "SUCCESS", "Succeeded Setting Service Parameters", ""
    else:
        return "FAILURE", "Failed Setting Service Parameters", "Failed Setting Service Parameters"