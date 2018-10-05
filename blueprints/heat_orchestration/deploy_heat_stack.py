from keystoneauth1 import session
import time
from infrastructure.models import CustomField
from orders.models import CustomFieldValue
from resourcehandlers.openstack.models import OpenStackHandler
from keystoneauth1.identity import v3
from heatclient import client

AUTH_URL = 'https://10.50.1.244:5000/v3'

def run():
    rh = OpenStackHandler.objects.first()
    auth = v3.Password(
        auth_url=AUTH_URL,
        username=rh.serviceaccount,
        password=rh.servicepasswd,
        project_name='admin',
        user_domain_id='default',
        project_domain_id='default')

    sess = session.Session(auth=auth, verify=False)
    heat = client.Client('1', session=sess)

    timestamp = str(time.time())
    timestamp, _ = timestamp.split('.')

    stack_name = "HEAT-{}".format(timestamp)
        #stack = heat.stacks.create()  # list(heat.stacks.list())

    response = heat.stacks.create(
        stack_name=stack_name,
        template_url='https://s3.amazonaws.com/hot-template/heat_stack.yml',
        parameters=[
            {'ParameterKey': 'db_name', 'ParameterValue': 'MyDatabase{}'.format(timestamp)},
            {'ParameterKey': 'db_password', 'ParameterValue': '{{DBPassword}}'},
            {'ParameterKey': 'db_root_password', 'ParameterValue': '{{DBRootPassword}}'},
            {'ParameterKey': 'db_user', 'ParameterValue': 'admin'},
            {'ParameterKey': 'image', 'ParameterValue': 'Ubuntu 14'},
            {'ParameterKey': 'key_name', 'ParameterValue': 'cb-key'},
            {'ParameterKey': 'db_port', 'ParameterValue': '50000'},
            {'ParameterKey': 'priv_net', 'ParameterValue': 'int-net'},
            {'ParameterKey': 'pub_net', 'ParameterValue': 'ext-net'},
            {'ParameterKey': 'flavor', 'ParameterValue': 'm1.small'},
        ],
    )

    logger.debug("Response: {}".format(response))
    stack_id = response['Id']

    resource = job.parent_job.resource_set.first()
    cf, _ = CustomField.objects.get_or_create(name="heat_stack_name", type="STR")
    cfv, _ = CustomFieldValue.objects.get_or_create(field=cf, value=stack_name)
    resource.attributes.add(cfv)
    return ("", "Stack installation initiated, the new stack has name {} and ID {}".format(stack_name, stack_id), "")
