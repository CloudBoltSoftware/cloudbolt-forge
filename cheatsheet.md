# CloudBolt Developers Cheatsheet:


## Commmon objects in CloudBolt:

## User 
The User object is the base object for all users in CloudBolt. It is the base object for the UserProfile object.

```python
from django.contrib.auth.models import User

user = User.objects.get(username='admin')

```

The user object has the following attributes:
```python
'last_login': datetime.datetime,
'is_superuser': True,
'username': 'admin',
'first_name': 'admin',
'last_name': 'admin',
'email': 'admin@cloudbolt.io',
'is_staff': True,
'is_active': True,
'date_joined': datetime.datetime
```
## UserProfile
Items of interest in UserProfile:
```python 
from accounts.models import UserProfile

up = UserProfile.objects.first()
up.first_initial_last
up.first_last_username
up.first_name_or_surname
up.full_name
```
The UserProfile object has the following attributes:
```python
 'id': 1,
 'global_id': 'USR-hn3zhlav',
 'catalog_viewing_mode': None,
 'user_id': 1,
 'tenant_id': None,
 'super_admin': True,
 'devops_admin': False,
 'api_access': True,
 'global_viewer': False,
 'ldap_id': None,
 'last_activity_time': datetime.datetime,
 'view_initial_tour': False,
```
## Server
The Server object is the base object for all servers in CloudBolt. It is the base object for the Server object.

```python
from infrastructure.models import Server

server = Server.objects.first()
```
The Server object has the following attributes:
```python
 'id': 1,
 'global_id': 'SVR-rlvplfly',
 'hostname': 'machine-hostname',
 'ip': '20.22.210.168',
 'mac': 'no:ma:ca:dd:re:ss',
 'os_build_id': None,
 'cpu_cnt': 2,
 'disk_size': 30,
 'mem_size': Decimal('8.0000'),
 'hw_rate': Decimal('0E-10'),
 'sw_rate': Decimal('0E-10'),
 'extra_rate': Decimal('0E-10'),
 'total_rate': Decimal('0E-10'),
 'notes': '',
 'add_date': datetime.datetime,
 'environment_id': 3,
 'owner_id': None,
 'status': 'ACTIVE',
 'group_id': 1,
 'provision_engine_svr_id': '',
 'provision_engine_id': None,
 'resource_handler_svr_id': '65433a13-425e-4771-9510-bf3468aabff5',
 'resource_handler_id': 1,
 'power_status': 'POWERON',
 'os_family_id': 2,
 'resource_id': None,
 'service_item_id': None,

```

## ResourceHandler
The ResourceHandler object is the base object for all connected resource handlers in CloudBolt. 

```python
from resourcehandlers.models import ResourceHandler

rh = ResourceHandler.objects.first()
```
The ResourceHandler object has the following attributes:
```python
 'id': 3,
 'global_id': 'RH-pdc8iurx',
 'real_type_id': 221,
 'name': 'AWS',
 'description': '',
 'tenant_id': None,
 'ip': 'aws.amazon.com',
 'port': 443,
 'protocol': '',
 'serviceaccount': 'AKIAXIX5IYHAP2A3ZGF6',
 'servicepasswd': 'Gjxxj0EuzzrtPZyeTd40JwaYAT4M4jf/F+VXjgSB',
 'resource_technology_id': 4,
 'ignore_vm_names': None,
 'ignore_vm_folders': None,
 'include_vm_tags': None,
 'enable_ssl_verification': False,
 'enable_console_feature': True,
 'enable_terminal_feature': False
```

## Group
The Group object is the base object for all groups in CloudBolt. 

```python
from accounts.models import Group

group = Group.objects.first()
```
The Group object has the following attributes:
```python
 'id': 2,
 'global_id': 'GRP-y01rgz9b',
 'name': 'Default',
 'description': None,
 'type_id': 3,
 'parent_id': 3,
 'levels_to_show': None,
 'allow_auto_approval': False,
 'quota_set_id': 9,
```

## Environment
The Environment object is the base object for all environments in CloudBolt. 

```python
from infrastructure.models import Environment

env = Environment.objects.first()
```
The Environment object has the following attributes:
```python
 'id': 9,
 'global_id': 'ENV-zvsfaaeb',
 'name': 'aws_environment',
 'description': None,
 'data_center_id': None,
 'resource_handler_id': 5,
 'provision_engine_id': None,
 'container_orchestrator_id': None,
 'tenant_id': None,
 'resource_pool_id': None,
 'auto_approval': False,
 'quota_set_id': 31,
 'rate_currency_unit': None
```


Install packages in XUI's frmo the shell or within a XUI

# Ensure pyYaml is installed, or install it.

from utilities.run_command import execute_command
try:
import pyYAML
except ImportError:
execute_command("pip install pyYAML")
import pyYAML

# Server Actions:

iterate through a list of servers in the job
for server in job.server_set.all()

Executing scripts remotely using a plug-in , this should utilize VMtools and bypass the need for WinRM.
def execute_script(self, script_path=None, script_contents=None,
script_args=None, timeout=120,
file_extension=None, runas_username=None,
runas_password=None, runas_key=None, run_with_sudo=False,
show_streaming_output=True):

                       for *NIX:
                       from common.methods import run_script_on_target_ssh

content = f"""
echo {resource.hostname}
"""
run_script_on_target_ssh(ip,none,content,username='ansible', key_name='ansible',key_location='global',timeout=120)

## Get or Create 
Get or create an object in the database. This is useful for creating a new object if it doesn't exist, or getting the existing object if it does.

This returns a tuple of (object, created), where created is a boolean specifying whether an object was created.

When assigning it to a variable, you can use the following syntax to get the object and ignore the created boolean:

If the object already exists, the object is returned and created is False.

If the object does not exist, the object is created and created is True. 

When the object is created using get_or_create(), the default values are used for any fields that are not specified. Pass these values in the defaults parameter.
```python
user, _ = User.objects.get_or_create(username='admin', defaults={
    'email': 'user@email.com'
    'first_name': 'first',
    'last_name': 'last',
    })

```

# Enable / disable maintenance mode
```bash
/opt/cloudbolt/utilities/maintenance_mode.py on
/opt/cloudbolt/utilities/maintenance_mode.py off
```

# bypass SSO only login
http://<cbhost>/accounts/login/?failure=True


# restarting services
```bash
supervisorctl restart jobengine:*
service httpd restart
```

# Cancel running sync vms job if you get this error:
A synchronization job for resource handler 'vCenter' is already running.
when trying to run a sync vms for resource handler job
```python
for lock in DBLock.objects.all():
    lock.delete()
```


# How to use Connection Info for username and password storage
```python
from utilities.models import ConnectionInfo

ci = ConnectionInfo.objects.get(name="CI Name")
username = ci.username
pwd = ci.password
```

# check to see if a server is ready
```python
server.wait_for_os_readiness()
```

# run an orchestration hook
```python
oh = OrchestrationHook.objects.get(id=175)
kwargs = {"server": server}
oh.run(**kwargs)
```

# how to use a key stored in cloudbolt for running a remote command
```python
from common.methods import run_script_on_target_ssh
content = f"""
    echo {resource.hostname}
"""
run_script_on_target_ssh(ip,none,content,username='ansible', key_name='ansible',key_location='global',timeout=120)
```

# how to get the api wrapper
```python
#rh = AzureARMHandler.objects.first()
rh = AWSHandler.objects.first()
w = rh.get_api_wrapper()
client = w.compute_client
```

# how to use the threadlogger
```python
from utilities.logger import ThreadLogger

if not logger:
    logger = ThreadLogger("__name__")

logger.info('Made it to here.')
```

# Call out to bash
```bash
subprocess.check_call(['chmod','+x',bash_file_path])

process = subprocess.Popen(["bash",bash_file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

output, error = process.communicate()

set_progress(output)
```


# set the ip on a server
```python
nic1 = server.nics.first()
nic1.ip = '10.1.1.1'
nic1.save()
server.save()
```

# how to get the vsphere API wrapper
```python
VsphereResourceHandler.objects.all()
vcenter = _[3]  # get the fourth one in the list from above
wrapper=vcenter.get_api_wrapper()
si = wrapper._get_connection()
```

# generate an options list from orchestration action
```python
def get_options_list(field, control_value=None, **kwargs):
    profile = kwargs.get("profile",None)
    email = [profile.user.email]
    return email
```


# generate an options list for an action input
```python
from common.methods import set_progress

def generate_options_for_adgroups(**kwargs):
    profile = kwargs.get("profile",None)
    options = []
    
    try:
        adgroups = profile.ldap.runUserSearch(profile.user.username, find=["memberOf"])
        for item in adgroups[0][1]['memberOf']:
            x = item.split(",")
            grp = x[0][3:]
            options.append((grp,grp))
    except:
        options.append(("Not an ldap user", "not an ldap user"))
    
    return options
```


# Find a items in vCenter via pyvmomi
```python
import pyVmomi
from resourcehandlers.vmware.pyvmomi_wrapper import get_vm_by_uuid
from infrastructure.models import Server


w = rh.get_api_wrapper()
si = w._get_connection()

vmbyid = get_vm_by_uuid(si, server.resource_handler_svr_id)

from resourcehandlers.vmware import pyvmomi_wrapper
obj = pyvmomi_wrapper.get_object_by_name(si, vim_class, obj_name)
# obj = pyvmomi_wrapper.get_object_by_name(si, [vim.Datastore], obj_name)

# print out recent tasks
for item in obj.recentTask:
    print(item.info)
```


# run a recurring job
```python
from jobs.models import RecurringJob

rj = RecurringJob.objects.get(id=2)
rj.spawn_new_job()
# Out[16]: <Job: Synchronize VMs from vCenter Job 128674>
```


# look for datastore size in vCenter
```python
rh=ResourceHandler.objects.get(id=1)
w = rh.get_api_wrapper()
si = w._get_connection()
datastore_name = "datastore_name"
datastore = w.get_object_by_name(si, pyVmomi.vim.StoragePod, datastore_name)
ds = datastore.summary.freeSpace
available_space = ds/1024/1024/1024
#available = str(round(available_space,2))
available = str(int(available_space))
print(available)
```


# sync an individual vm from vCenter
```python
vm = {}
vm['hostname'] = server.hostname
vm['uuid'] = server.resource_handler_svr_id
vm['power_status'] = 'POWERON'

group=server.group.name
env=server.environment.name
owner=server.owner.full_name
rh = VsphereResourceHandler.objects.first()

from jobengine.jobmodules.syncvmsjob import SyncVMsClass
sync_class = SyncVMsClass()
(newserver, status, errors) = sync_class.import_vm(vm, rh, group, env, owner)
```


# update tags
```python
cf =  CustomField.objects.get(name='URL_2')
server.set_value_for_custom_field(cf,'CloudTagissue-2.mdsol.com')
server.save()
rh = server.resource_handler.cast()
rh.update_tags(server)
```


# Run remote commands
```python
from utilities.run_command import run_command, execute_command
from common.methods import find_key_material

#x=SSHKey.objects.get(name='my-key-pair2')
#x.storedsshkey.private_key

"""
`key_location` is either a RH or the string 'global' if the key name is for a Global key not associated with a RH.
"""
_,keyfile = find_key_material("ansible-key", key_location="global")
keyfile_args = "-i '{}'".format(keyfile)

cmd = f"ssh {keyfile_args} user@ansibleserver ansible-playbook -i inventory cb_test.yml"
execute_command(cmd)


run_command(cmd,
    strip=None,
    logoutput=True,
    env=None,
    output_subs=None,
    realtime_logging=True,
    cwd=None,)


execute_command(
    command,
    timeout=120,
    strip=None,
    stream_title="",
    stdout_file=None,
    stderr_file=None,
    stream_remote_output=True,
    run_synchronously=True,
)
```


# server execute remote commands
```python
server.execute_script(self, script_path=None, script_contents=None,
                       script_args=None, timeout=120,
                       file_extension=None, runas_username=None,
                       runas_password=None, runas_key=None, run_with_sudo=False,
                       show_streaming_output=True)

mykey = {"name": "myCentos", "is_global": True}
cmd = "whoami"
server = Server.objects.get(id=641)
server.execute_script(script_contents=cmd,runas_key=mykey)
```


# add parameter (a.k.a custom field value)
```python
inet_allocated_ip_cf, _ = CustomField.objects.get_or_create(
    name='inet_allocated_ip_address',
    label='Inet IpAddress',
    type='STR',
    description='The IpAddress allocated in Inet.',
    show_on_servers=True
)

inet_allocated_ip = "1.1.1.2"

inet_allocated_ip_cfv, _ = CustomFieldValue.objects.get_or_create(field=inet_allocated_ip_cf,
                                                                 value=inet_allocated_ip)

inet_allocated_ip_cfv.value = "1.1.1.2"

server.custom_field_values.add(inet_allocated_ip_cfv)

server.save()
# server.inet_allocated_ip_address = '1.1.1.2'
```


# see the sample payload for a blueprint
```python
import json
from servicecatalog.services.blueprint_service import BlueprintService
from servicecatalog.models import ServiceBlueprint

options = []
for bp in ServiceBlueprint.objects.filter(status="ACTIVE"):
    bp_dict = {"id": bp.global_id, "name": bp.name}
    options.append(bp_dict)
    print(bp.global_id, bp.name)

for bp in ServiceBlueprint.objects.filter(status="ACTIVE"):
    print(f"{bp.name}: {bp.global_id}")
    for si in bp.deployment_sis().all():
        print(f"\t{si.name}: {si.cast().slug}")
        print("\n")

    service = BlueprintService(bp)

    group = Group.objects.get(name="Sales Engineers")
    profile = UserProfile.objects.first()
    try:
        _, sample_payload = service.sample_payload(profile, group)
        print(json.dumps(sample_payload, indent=4))
    except:
        pass
```


# see parameters in an order
```python
   
#bpia = bp_order_item.blueprintitemarguments_set.filter(environment__isnull=False).first()
from common.methods import set_progress

def run(job, *args, **kwargs):
    order = job.parent_job.get_order()
    order_item = order.orderitem_set.filter(blueprintorderitem__isnull=False).first()
    bp_order_item = order_item.blueprintorderitem
    bpia = bp_order_item.blueprintitemarguments_set.first()
    
    bpia.custom_field_values.all()
    
    for oi in  bpia.custom_field_values.all():
        set_progress(f"{oi.field.name} is {oi.value}")

    return "SUCCESS", "Sample output message", ""
```


# get order informtion
```python
order = Order.objects.get(id=304)
bp_order_item = order.orderitem_set.filter(blueprintorderitem__isnull=False).first()

for bpoi in bp_order_item.blueprintorderitem.blueprintitemarguments_set.all():
    print(f"Build item: {bpoi}")
    if bpoi.environment:
        print(f"Environment: {bpoi.environment}")
        print(f"Resouorce Handler: {bpoi.environment.resource_handler}")
        bpoi.custom_field_values.all()
        for cfv in  bpoi.custom_field_values.all():
            print(f"Parameters: {cfv}")
```

# Inbound web hook 
```python
from common.methods import set_progress
from infrastructure.models import Server
from common.methods import create_decom_job_for_servers

def inbound_web_hook_post(*args, parameters={}, **kwargs):
    hostname = parameters["servername"]
    
    try:
        server = Server.objects.get(status="ACTIVE", hostname=hostname)
        jobs = create_decom_job_for_servers([server])
        job = jobs[0]

        msg = f"Decommission the server named: {hostname}, job: {job}"

    except:
        msg = f"No Active server found with hostname of {hostname}"
    
    return msg
```


# Call the webhook
```python
# Inbound web hook POST -- uses json= instead of params= (like the GET)
import json, requests, sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://cbhostname/api/v3/cmp/inboundWebHooks/global_id/run/?token=xxxxx"

response = requests.post(url, verify=False, json={'servername': 'Dev-125'})

print(response.text)
```

# Increase the number of jobengine workers
```bash
# Number of Processes:  By default, the CloudBolt appliance only runs one Job Engine process at a time. 
# That process creates threads to run individual jobs. It could improve performance for customers to increase 
# the number of Job Engine processes that run simultaneously, as each process can run on a separate CPU core.
# To increase the number of simultaneous Job Engine processes:
#•   Edit the /etc/supervisord.d/jobengine.conf configuration file.
#•   Change the line that starts with numprocs to indicate the desired number of simultaneous Job Engine 
#processes (e.g. numprocs=3)
#•   Once no jobs are running, reload the Job Engine for these new settings to take effect. 
#Use the command supervisorctl reload.
```

# Fix the WARNINGS 'encoded with obsolete method. Decrypting accordingly' in job logs
```python
# We used this code to re-save values using obsolete methods. 
# The only real issue was the amount of time it takes to save millions of CustomFieldValue objects.

for ci in ConnectionInfo.objects.all():
    ci.save()

for cfv in CustomFieldValue.objects.exclude(pwd_value=''):
    if hasattr(cfv, 'pwd_value') and cfv.pwd_value is not None and cfv.pwd_value != '':
        cfv.save()
```


#Add tag to servers
```python
import os, sys

from jobs.models import Job

def run(job, logger=None, **kwargs):
    servers = job.server_set.all()
    if not servers:
        return "WARNING", "", "No server in job"
    # Add the tags
    tags_string = "{{TAGS}}"
    for server in servers:
        tags = tags_string.split(",")
        for tag in tags:
            server.tags.add(tag.strip())

    return "", "", ""
```

# add tags to aws vm
```python
from resourcehandlers.aws.models import AWSHandler

aws = AWSHandler.objects.first()

s=Server.objects.get(id=297)

wrapper = aws.get_api_wrapper(region_name=s.environment_aws_region)

tags_dict={'Name':'test01.AWS-East'}

wrapper.update_instance_tags(s.resource_handler_svr_id,tags_dict)
```


# How to get the email settings
```python
gp = GlobalPreferences.objects.first()
gp.smtp_host
gp.smtp_port
gp.smtp_user
gp.smtp_password
```

# Enable cancel orphan jobs
```bash
# vi customer_settings.py
from settings import FEATURE_REGISTRY
FEATURE_REGISTRY["jobengine::cancel_orphan_jobs"] = False
```


# search job progress messages
```python
ansible_build_step_id = 2
bp_id = job.parent_job.children_jobs.all()[ansible_build_step_id]
bp_job = Job.objects.get(id=bp_id)

for pm in bp_job.progressmessage_set.all():
    if "Done running remote command on xyz" in pm.message:
        print(pm.detailed_message)
```


# write a progress message or a detailed progress message
```python
from jobs.models import Job, ProgressMessage
 
def run(job, *args, **kwargs):
    pm = ProgressMessage(job=job, message="Hello from CloudBolt")  # normal set progress
    pm.detailed_message = "Hello World"  # like remote script, in a show details pane
    pm.save()
    
    return "SUCCESS", "Sample output message", ""
 ```

# bulk remove networks on an environment
```python
nets_to_remove = env.get_possible_networks().exclude(name__in=["a", "b", "c"])
for net in nets_to_remove:
    env.remove_network(net.resourcenetwork_ptr, 1)
 ```

# call a CloudBolt Remote Script
```python
remotescript = RemoteScriptHook.objects.filter(name=script_name).first()

remotescripthook_jobs = remotescript.run(
parent_job=job,
server=server,
script_password=server.password,
script_username=server.owner.username)
 ```



