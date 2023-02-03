## BLUEPRINT FOR GROUP SELF SERVICE CREATION
## DESCRIPTION:
## The following blueprint provides for the customer the ability to provision in self service the group in cloubolt
## Once the group is created, we assign  to the requestor all the roles.
## A group could has two types : Standard or lab
## Standard is a permanent group with no limit in times
## Lab is limited to specific period of time (per default 3 months).
## INPUTS:
## group_name : Name of the Group
## group_description : Describe the group
## group_quota: Selcet the quo limitation
##
from django.core.exceptions import ObjectDoesNotExist
from accounts.models import Group, GroupRoleMembership
from accounts.models import GroupType
from accounts.models import Role
from servicecatalog.models import ServiceItem, ServiceBlueprint, ServiceBlueprintGroupPermissions
from quota.models import Quota
from quota.models import ServerQuotaSet
from common.methods import set_progress
from decimal import Decimal
from datetime import datetime
from dateutil.relativedelta import relativedelta



def run(job, **kwargs):
    set_progress("Using input parameters")

    group_name = '{{group_name}}'
    project_description = '{{project_description}}'
    owner_department = '{{owner_department}}'
    group_type_selection = '{{group_type_selection}}'
    expiration_date = '{{expiration_date}}'
    cost_center = '{{cost_center}}'
    group_quotas = '{{group_quota}}'
    group_type = None
    parent_group_name="My_parent_group"
    months_extension=3


group_parent = None
# Here is the user executing the blueprint
user_profile = job.owner

info = group_quotas.split(";")  # [0] == CPU // [1] == RAM // [2] == STORAGE

set_progress("Searching for GroupType...")

try:
    group_type = GroupType.objects.get(group_type=group_type_selection)
except ObjectDoesNotExist:
    group_type = GroupType.objects.create(group_type=group_type_selection)
try:
    group_found = Group.objects.get(name=group_name)
    set_progress(group_found.found.get_value_for_custom_field(cf_name='my_department'))
    raise Exception('Project already exist.')
except ObjectDoesNotExist:

    set_progress("Creating Group...")

try:
    # Define Group Quota
    set_progress("Creating Quota...")
    limit_cpu = Decimal(info[0])
    limit_ram = Decimal(info[1])
    limit_disk = Decimal(info[2])

    cpu = Quota.objects.create(limit=limit_cpu)
    ram = Quota.objects.create(limit=limit_ram)
    disk = Quota.objects.create(limit=limit_disk)
    group_quota_set = ServerQuotaSet.objects.create(cpu_cnt=cpu, mem_size=ram, disk_size=disk)
    set_progress("Quota set...")
    set_progress("Creating the Group...")
    # Create the Group following a name template
    group_parent = Group.objects.get(name=parent_group_name)
    group = Group.objects.create(name=group_name, description=project_description, type=group_type, parent=group_parent,
                                 quota_set=group_quota_set)
    # Associate the department of the owner
    set_progress("Allocating the Customer Department ...")
    group.set_value_for_custom_field(cf_name='my_department', value=owner_department)
    myvalue = group.get_value_for_custom_field(cf_name='my_department')

    if group_type_selection == 'lab':
        set_progress("Allocating the Project Time expiration ...")
        group.get_value_for_custom_field(cf_name='expiration_date', value=datetime.datetime.today() + relativedelta(months=+months_extension))

except ObjectDoesNotExist:
    group.delete()
    raise Exception('Project creation error. Please contact the administrator')

try:

    set_progress("Allocate the Role for the user...")

    # Get the list of roles
    roles = Role.objects.filter(name__in=("viewer", "requestor", "approver", "resource_admin", "group_admin"))
    #  Add each roles for the user
    for role in roles:
        user_profile.add_role_for_group(role, group)

    set_progress("Assigning Deploy rights on Blueprint...")
    # List all the blueprint
    serviceblueprints = ServiceBlueprint.objects.all().exclude(name="Project")
    set_progress("Number of Blueprint is %s" + str(serviceblueprints.count()))

    for serviceblueprint in serviceblueprints:
        set_progress("Assigning Deploy Right to %s" + serviceblueprint.name)
        ServiceBlueprintGroupPermissions.objects.create(blueprint=serviceblueprint, group=group,
                                                        permission="Deploy")
    return "", "", ""
except ObjectDoesNotExist:
    raise Exception('Role or Blueprint right allocation error. Please contact the administrator')


# List of group type
# return a group_type
def generate_options_for_group_type_selection(**kwargs):
    return [('standard', 'standard'), ('lab', 'lab'), ]


# List of quota flavors
# return a quota flavor
def generate_options_for_group_quota(**kwargs):
    data = {
        "plans": [
            {
                "cpu": "1",
                "ram": "1",
                "storage": "60",
            },
            {
                "cpu": "2",
                "ram": "2",
                "storage": "60"
            },
            {
                "cpu": "2",
                "ram": "4",
                "storage": "60"
            },
            {
                "cpu": "2",
                "ram": "8",
                "storage": "60",
            },
            {
                "cpu": "2",
                "ram": "16",
                "storage": "60"
            },
            {
                "cpu": "4",
                "ram": "4",
                "storage": "60"
            },
            {
                "cpu": "4",
                "ram": "8",
                "storage": "60"
            },
            {
                "cpu": "4",
                "ram": "16",
                "storage": "60"
            },
            {
                "cpu": "4",
                "ram": "32",
                "storage": "60"
            },
            {
                "cpu": "8",
                "ram": "8",
                "storage": "60"
            },
            {
                "cpu": "8",
                "ram": "16",
                "storage": "60"
            },
            {
                "cpu": "8",
                "ram": "32",
                "storage": "60"
            },
            {
                "cpu": "8",
                "ram": "64",
                "storage": "60"
            },
            {
                "cpu": "16",
                "ram": "16",
                "storage": "60"
            },
            {
                "cpu": "16",
                "ram": "32",
                "storage": "60"
            },
            {
                "cpu": "16",
                "ram": "64",
                "storage": "60"
            },
        ]
    }

    my_prices = []
    if len(data) != 0:
        for plan in data['plans']:
            cpu = plan['cpu']
            ram = plan['ram']
            storage = plan['storage']
            price = "CPU : %s, RAM : %s GB, STORAGE : %s GB" % (cpu, ram, storage)
            my_prices.append((cpu + ";" + ram + ";" + storage, price))

    return my_prices
