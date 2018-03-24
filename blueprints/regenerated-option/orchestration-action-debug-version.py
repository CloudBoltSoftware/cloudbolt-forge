#!/usr/bin/env python

# Author: Steven Manross
# Partner: Riverturn, Inc
# Name: Regenerate Options For Monitoring Group
# Modified: 
#          3/16/2018 1.0  smanross   initial revision
#          3/16/2018 1.1  smanross   added logic for customized monitoring_groups tailored to Cloudbolt groups and monitoring_tools
# Tested using Cloudbolt version: 7.7.2
# Description: 
#             Generate an option list for the parameter: "monitoring_group" based on a "monitoring tool" name
# Requires: 
#             *Cloudbolt Parameters: enable_mointoring (boolean), monitoring_tool (string), monitoring_group (string)
#             *FieldDependency: monitoring_group is dependent on monitoring_tool (type: Regenerate Options)
#             *Modify the mon_groups structure in this code to match your Cloudbolt group list by changing the followng groups
#                  below and/or adding more entries:
#                      "Information Technology"
#                      "Finance"
#                      "Sales"
#                      "Riverturn"
#             --> There is code in this Orchestration Action that can be removed AFTER the required parameters have been created
#                     & the FieldDependency has been set (this code will run the first time you try and order the test blueprint).
#                     --> From a performance perspective, you shouldn't need this code after it initially runs and should disable it

from infrastructure.models import CustomField,FieldDependency
#from utilities.logger import ThreadLogger
from accounts.models import Group

def get_options_list(field, blueprint=None, group=None, **kwargs):

    if field.name == 'monitoring_group':
        #start - you can remove this after the Parameters are created and the dependency is set initially on your cloudbolt server

        #create the required parameters in Cloudbolt
        em, _ = CustomField.objects.get_or_create(name="enable_monitoring", label="Enable Monitoring",type='BOOL')
        mt, _ = CustomField.objects.get_or_create(name="monitoring_tool", label="Monitoring Tool",type='STR')
        mg, _ = CustomField.objects.get_or_create(name="monitoring_group", label="Monitoring Group",type='STR')

        #find out if the dependency is set already
        found = 0
        for fd in FieldDependency.objects.all():
            if fd.controlling_field_id == mt.id and fd.dependent_field_id == mg.id and fd.dependency_type == "REGENOPTIONS":
                found = 1
                #all good .. the dependency is set
                break
        if found == 0:
            #create the FieldDependency with the required options
            newfd = FieldDependency.objects.create(dependent_field_id=mg.id, controlling_field_id=mt.id, dependency_type='REGENOPTIONS')

        em = None
        mt = None
        mg = None
        newfd = None
        #end - you can remove this code after the Parameters are created and the dependency is set initially on your cloudbolt server

        #logger = ThreadLogger('__name__')

        form_prefix = kwargs.get('form_prefix')
        form_data = kwargs.get('form_data')
        mon_tool_dict = field.get_control_values_from_form_data(form_prefix=form_prefix, form_data=form_data)

        #define the monitoring tool, along with the group options for each
        #    or come up with some code that dynamically gets this information from somewhere into a similar structure

        group_object = None
        order_group_id = 0
        if form_data is not None  and 'order_group' in form_data:
            order_group_id = form_data['order_group'][0]

        mon_groups = {
            'Finance': {
                'Zabbix': [
                    ('finance-group1-zabbix', 'finance-group2-zabbix'),
                    ('finance-group2-zabbix', 'finance-group2-zabbix'),
                          ],
                'ServiceNow': [
                    ('finance-group1-snow', 'finance-group1-snow'),
                    ('finance-group2-snow', 'finance-group2-snow'),
                ],
            },
            'Information Technology': {
                'Zabbix': [
                    ('it-group1-zabbix', 'it-group1-zabbix'),
                    ('it-group2-zabbix', 'it-group2-zabbix'),
                          ],
                'ServiceNow': [
                    ('it-group1-snow', 'it-group1-snow'),
                    ('it-group2-snow', 'it-group2-snow'),
                ],
            },
            'Sales': {
                'Zabbix': [
                    ('sales-group1-zabbix', 'sales-group1-zabbix'),
                    ('sales-group2-zabbix', 'sales-group2-zabbix'),
                          ],
                'ServiceNow': [
                    ('sales-group1-snow', 'sales-group1-snow'),
                    ('sales-group2-snow', 'sales-group2-snow'),
                ],
            },
            'Riverturn': {
                'Zabbix': [
                    ('rt-group1-zabbix', 'rt-group1-zabbix'),
                    ('rt-group2-zabbix', 'rt-group2-zabbix'),
                          ],
                'ServiceNow': [
                    ('rt-group1-snow', 'rt-group1-snow'),
                    ('rt-group2-snow', 'rt-group2-snow'),
                ],
            },
        }

        options = []
        options.append(('', '--------')) #put an entry in the list so we don't default to a valid value and require use input

        if order_group_id != 0:
            group_object = Group.objects.get(id=order_group_id)
        else:
            #similar condition to below, but...  if the order_group_id isnt parsed from the form_data correctly, add all the options (could be validation issues like below, or possibly
            #    a true error getting information from the form_data)
            options = [] #get rid of the empty entry above in case we are validating (which will cause the order not to process)
            for grpkey in mon_groups:
                for toolkey in mon_groups[grpkey]:
                    for opt in mon_groups[grpkey][toolkey]:
                        options.append(opt)
            
        if type(mon_tool_dict) is dict:
            mon_tool_val = mon_tool_dict['monitoring_tool'][0]

            found_items = 0
            if mon_groups.has_key(group_object.name):
                if mon_groups[group_object.name].has_key(mon_tool_val):
                    found_items = 1
                    for opt in mon_groups[group_object.name][mon_tool_val]:
                        options.append(opt)

            if found_items == 0:
                # if we are getting here, there's a problem with the monitoring_tool name (it didnt match our known values, so assume that you didnt select a monitoring_tool)
                options = [('---','No Monitoring Tool Selected')]
        else:
            #when you press submit on the order page, the app validates the group name chosen, but the form_data and form_prefix
            #   are not available which makes the code fail unless you list all the possible parameters from this code block (because you dont know which monitoring_group
            #   was chosen)
            options = [] #get rid of the empty entry above in case we are validating (which will cause the order not to process)
            for grpkey in mon_groups:
                for toolkey in mon_groups[grpkey]:
                    for opt in mon_groups[grpkey][toolkey]:
                        options.append(opt)

        return {'options': options}