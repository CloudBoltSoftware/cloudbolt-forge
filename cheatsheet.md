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


