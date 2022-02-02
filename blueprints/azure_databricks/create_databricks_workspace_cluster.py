"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
import requests
import json
import time
from common.methods import set_progress
from infrastructure.models import CustomField, Environment, Server
from resourcehandlers.azure_arm.models import AzureARMHandler
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


"""
Todo - Pending feature
1. Create Job
2. Create Table
3. Create Notebook
API reference - https://docs.microsoft.com/en-gb/azure/databricks/dev-tools/api/latest/
"""

def get_or_create_custom_fields():
    """ 
    Get or create a new custom fields
    """
    CustomField.objects.get_or_create(
        name="dbs_cluster_name",
        type="STR",
        defaults={
            'label': "Cluster Name",
            'description': 'Used by the ARM Template blueprint.',
            'required': False,
        }
    )
    
    CustomField.objects.get_or_create(
        name="dbs_runtime_version",
        type="STR",
        defaults={
            'label': "Databricks runtime version",
            'description': 'Used by the ARM Template blueprint.',
            'required': True,
        }
    )
    
    CustomField.objects.get_or_create(
        name="dbs_worker_type",
        type="STR",
        defaults={
            'label': "Worker Type",
            'description': 'Used by the ARM Template blueprint.',
            'required': True,
        }
    )
    
    CustomField.objects.get_or_create(
        name="dbs_num_workers",
        type="INT",
        defaults={
            'label': "Number Workes",
            'description': 'Used by the ARM Template blueprint.',
            'required': True,
        }
    )
    
    CustomField.objects.get_or_create(
        name="autotermination_minutes",
        type="INT",
        defaults={
            'label': "Terminate after",
            'description': 'the cluster will terminate after the specified time interval of inactivity (i.e., no running commands or active job runs). This feature is best supported in the latest Spark versions',
            'required': True,
        }
    )

def get_token(rs, client_id, client_secret, tenantId):
    '''
    Generate AD and Management Access Token
    '''
    
    as_header = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'resource': rs
    }
    
    # get token
    resp = requests.get(f'https://login.microsoftonline.com/{tenantId}/oauth2/token', headers= as_header, data=data)

    if resp.status_code != 200:
        raise RuntimeError("Unable to get AD or Management access token")

    return resp.json()['access_token']

def create_databricks_cluster(rh, resource_group, dbricks_workspace, dbricks_location, cluster_kwargs, count=0):
    ''' Create databricks workspace cluster'''

    # Get a token for the global Databricks application. This value is fixed and never changes.
    adbToken = get_token("2ff814a6-3304-4ab8-85cb-cd0e6f879c1d", rh.client_id, rh.secret, rh.azure_tenant_id)

    # Get a token for the Azure management API
    azToken = get_token("https://management.core.windows.net/", rh.client_id, rh.secret, rh.azure_tenant_id)
    
    dbricks_auth = {
        "Authorization": f"Bearer {adbToken}",
        "X-Databricks-Azure-SP-Management-Token": azToken,
        "X-Databricks-Azure-Workspace-Resource-Id": (
            f"/subscriptions/{rh.serviceaccount}"
            f"/resourceGroups/{resource_group}"
            f"/providers/Microsoft.Databricks"
            f"/workspaces/{dbricks_workspace}")}
    
    dbricks_api = f"https://{dbricks_location}/api/2.0"
    

    # create databricks workspace cluster
    ds_rsp = requests.post(f"{dbricks_api}/clusters/create", headers= dbricks_auth, data=json.dumps(cluster_kwargs))
    result = ds_rsp.json()
    
    if ds_rsp.status_code == 200:
        return result
        
    logger.info("Got this error when creating a cluster after creating a workspace : %s", result)
    
    if count < 2:
        logger.info("Databricks cluster params %s", cluster_kwargs)
        
        # system got UnknownWorkerEnvironmentException when creating a cluster after creating a workspace
        # https://github.com/databrickslabs/terraform-provider-databricks/issues/33
        time.sleep(60)
        
        logger.info("retry to create cluster after 60 seconds sleep")
        
        # retry create databricks cluster
        create_databricks_cluster(rh, resource_group, dbricks_workspace, dbricks_location, cluster_kwargs, count+1)

    raise RuntimeError(result) 


def generate_options_for_dbs_runtime_version(field, **kwargs):
    return [ ('10.3.x-scala2.12', '10.3 Beta (Apache Spark 3.2.0, Scala 2.12)'),
        ('10.2.x-scala2.12', '10.2 (Apache Spark 3.2.0, Scala 2.12)'),
        ('10.1.x-scala2.12', '10.1 (Apache Spark 3.2.0, Scala 2.12)'),
        ('10.0.x-scala2.12', '10.0 (Apache Spark 3.2.0, Scala 2.12)'),
        ('9.1.x-scala2.12', '9.1 LTS (Apache Spark 3.1.2, Scala 2.12)'),
        ('9.0.x-scala2.12', '9.0 (Apache Spark 3.1.2, Scala 2.12)'),
        ('7.3.x-scala2.12', '7.3 LTS (Apache Spark 3.0.1, Scala 2.12)'),
        ('6.4.x-esr-scala2.11', '6.4 Extended Support (Apache Spark 2.4.5, Scala 2.11)')]
    

def generate_options_for_dbs_worker_type(field, **kwargs):
   return  [('Standard_DS3_v2', 'Standard_DS3_v2 (14 GB Memory, 4 Cores)'), 
    ('Standard_DS4_v2', 'Standard_DS4_v2 (28 GB Memory, 8 Cores)'), 
    ('Standard_DS5_v2', 'Standard_DS5_v2 (56 GB Memory, 16 Cores)'), 
    ('Standard_D3_v2', 'Standard_D3_v2 (14 GB Memory, 4 Cores)'), 
    ('Standard_D4_v2', 'Standard_D4_v2 (28 GB Memory, 8 Cores)'), 
    ('Standard_D5_v2', 'Standard_D5_v2 (56 GB Memory, 16 Cores)'), 
    ('Standard_D12_v2', 'Standard_D12_v2 (28 GB Memory, 4 Cores)'), 
    ('Standard_D13_v2', 'Standard_D13_v2 (56 GB Memory, 8 Cores)'), 
    ('Standard_DS12_v2', 'Standard_DS12_v2 (28 GB Memory, 4 Cores)'), 
    ('Standard_DS13_v2', 'Standard_DS13_v2 (56 GB Memory, 8 Cores)'), 
    ('Standard_H8', 'Standard_H8 (56 GB Memory, 8 Cores)'),
    ('Standard_NC4as_T4_v3', 'Standard_NC4as_T4_v3 (28 GB Memory, 4 Cores)'),
    ('Standard_NC8as_T4_v3', 'Standard_NC8as_T4_v3 (56 GB Memory, 8 Cores)')]


def run(job, *args, **kwargs):
    cluster_name =  '{{dbs_cluster_name}}'
    
    if cluster_name.strip() == "":
        return "", "", ""
    
    set_progress("Starting Provision of the databricks workspace cluster...")
    logger.info("Starting Provision of the databricks workspace cluster...")
    
    resource = kwargs.get('resource')
    
    # create custom fields if not exists
    get_or_create_custom_fields()
    
    create_cluster_params = {
        'cluster_name': cluster_name,
        'spark_version': '{{dbs_runtime_version}}',
        'node_type_id': '{{dbs_worker_type}}',
        'num_workers': '{{dbs_num_workers}}',
        'autotermination_minutes':  '{{autotermination_minutes}}'
    }
    
    logger.info("Databricks worspace cluster params : %s", create_cluster_params)
    
    # get resource handler object
    rh = AzureARMHandler.objects.get(id=resource.azure_rh_id)
    
    # deploy databricks workspace cluster
    clust_resp = create_databricks_cluster(rh, resource.resource_group, resource.name, resource.azure_dbs_workspace_url, create_cluster_params)
    
    # create cluster server
    server = Server.objects.create(
        hostname=cluster_name,
        resource_handler_svr_id=clust_resp['cluster_id'],
        environment=Environment.objects.get(resource_handler_id=resource.azure_rh_id, node_location=resource.azure_region),
        resource_handler=rh,
        group=resource.group,
        owner=resource.owner,
    )
    
    resource.server_set.add(server)
        

    return "SUCCESS", "Databricks workspace cluster deployed successfully", ""