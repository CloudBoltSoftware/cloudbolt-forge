from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
from common.methods import set_progress
from infrastructure.models import CustomField, Environment
from pathlib import Path
import json, tempfile
import os
import zipfile
import time
import io
from django.conf import settings
from googleapiclient.http import MediaIoBaseUpload


def generate_custom_fields():
    CustomField.objects.get_or_create(
        name='function_name', defaults={'label': 'function name', 'type': 'STR', 'show_as_attribute': True,
                                        'description': 'Name given to the Google Cloud function'}
    )
    CustomField.objects.get_or_create(
        name='available_memory_mb', defaults={'label': 'Memory', 'type': 'INT', 'show_as_attribute': True,
                                              'description': 'Memory allocated to the Google Cloud function'}
    )
    CustomField.objects.get_or_create(
        name='entry_point', defaults={'label': 'EntryPoint', 'type': 'STR', 'show_as_attribute': True,
                                      'description': 'Name of a function exported by the module specified in '
                                                     'directory with source code'}
    )
    CustomField.objects.get_or_create(
        name='runtime', defaults={'label': 'Runtime', 'type': 'STR', 'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='service_account_email', defaults={'label': 'serviceAccountEmail',
                                                'type': 'STR',
                                                'show_as_attribute': False,
                                                'description':
                                                    'Service account that the function will assume as its identity.'}
    )
    CustomField.objects.get_or_create(
        name='https_trigger', defaults={'label': 'HttpsTrigger',
                                        'type': 'STR',
                                        'show_as_attribute': True,
                                        'description':
                                            'Url to trigger the google function'}
    )
    CustomField.objects.get_or_create(
        name='source_archive_url', defaults={'label': 'sourceArchiveUrl',
                                             'type': 'STR',
                                             'show_as_attribute': True,
                                             'description':
                                                 'Url to where the source code of the function is located.'}
    )
    CustomField.objects.get_or_create(
        name='google_rh_id', defaults={'label': 'Resource Handler',
                                       'type': 'STR',
                                       'show_as_attribute': False})


FUNCTIONS_VALID_REGIONS = ['us-central1', 'us-east1',
                           'asia-east2', 'asia-northeast1', 'europe-west1', 'europe-west2']


def generate_options_for_env_id(server=None, **kwargs):
    gcp_envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Google Cloud Platform")
    options = []
    for env in gcp_envs:
        options.append((env.id, env.name))
    if not options:
        raise RuntimeError("No valid Google Cloud Platform resource handlers in CloudBolt")
    return options


def generate_options_for_runtime(**kwargs):
    return [("nodejs8", "Node JS 8"),
            ("nodejs10", "Node JS 10"),
            ("python37", "Python 3.7"),
            ("go111", "Node JS 8"), ]


def generate_options_for_bucket_to_store_sourcecode(control_value=None, **kwargs):
    buckets = []
    if control_value:
        environment = Environment.objects.get(id=control_value)
        project_id=environment.gcp_project
        rh = environment.resource_handler.cast()
        project=rh.gcp_projects.get(id=project_id).name
        storage_client = create_build_client(rh,project_id,'storage')
        list_bucket=storage_client.buckets().list(project=project).execute()
        buckets = [bucket.get('name') for bucket in list_bucket.get('items')]

    return buckets


def generate_options_for_enter_sourcecode_or_bucket_url(**kwargs):
    return ['SourceCode', 'BucketUrl']


def generate_options_for_available_memory_mb(**kwargs):
    return [
        (128, '128 MB'),
        (256, '256 MB'),
        (512, '512 MB'),
        (1024, '1 GB'),
        (2048, '2 GB'),
    ]

def generate_options_for_gcp_region(control_value=None,**kwargs):
    if control_value is None:
        return []
    environment = Environment.objects.get(id=control_value)
    project_id=environment.gcp_project
    rh = environment.resource_handler.cast()
    project=rh.gcp_projects.get(id=environment.gcp_project).name
    client = create_build_client(rh,project_id,'cloudfunctions')
    locations=client.projects().locations().list(name=f'projects/{project}').execute()
    return [region.get('locationId') for region in locations['locations']]

def create_build_client(rh,project_id,servicename):
    '''method to create cloud build client for given service''' 
    account_info = json.loads(rh.gcp_projects.get(id=project_id).service_account_info)
    credentials=service_account.Credentials.from_service_account_info(account_info)
    client=build(servicename, "v1", credentials=credentials, cache_discovery=False)
    return client



def validate_file_name(runtime,filename):
    """
    Every runtime has
        -specific file that is expected by google cloud functions
    """
    runtimes = {
        'python37': 'main.py',
        'nodejs8': 'index.js',
        'nodejs10': 'index.js',
        'go111': 'function.go'
    }
    return (runtimes.get(runtime)==filename)


def create_file_with_sourcecode(sourcecode):
    # Creates a temporary file containing the sourcecode passed.
    path=sourcecode
    filename=Path(sourcecode).name
    if path.startswith(settings.MEDIA_URL):
        set_progress("Converting relative URL to filesystem path")
        path = path.replace(settings.MEDIA_URL, settings.MEDIA_ROOT)
    path = os.path.join(settings.MEDIA_ROOT, path)
    archive=io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as zip_archive:
        with open(path, 'r') as file:
            zip_file = zipfile.ZipInfo(filename)
            zip_archive.writestr(zip_file, file.read())
    archive.seek(0)
    media=MediaIoBaseUpload(archive, mimetype='application/zip')
    return media


def upload_file_to_s3(storage_client, bucket_name, file,func_name):
    '''method to upload file in bucket'''
    body={'name': func_name}
    object=storage_client.objects()
    obj_insert=object.insert(bucket=bucket_name,body=body,media_body=file).execute()
    return bucket_name+'/'+func_name


def run(resource, logger=None, **kwargs):
    environment = Environment.objects.get(id='{{ env_id }}')
    function_name = '{{ function_name }}'
    source_code = """{{ source_code }}"""
    entry_point = '{{ entry_point }}'
    available_memory_mb = '{{ available_memory_mb }}'
    runtime = '{{ runtime }}'
    bucket = '{{ bucket_to_store_sourcecode }}'
    cloud_storage_location = '{{ cloud_storage_location }}'
    enter_sourcecode_or_bucket_url = "{{enter_sourcecode_or_bucket_url}}"
    region = "{{gcp_region}}"
    rh = environment.resource_handler.cast()
    
    
    project = environment.gcp_project
    account_info = json.loads(rh.gcp_projects.get(id=project).service_account_info)
    project_name=account_info['project_id']

    service_name = 'cloudfunctions'
    
    client = create_build_client(rh,project,service_name)

    set_progress("Connection to google cloud established")

    # validate a file with an extension corresponding to the runtime selected
    
    
    storage_client = create_build_client(rh,project,'storage')

    if not cloud_storage_location:
        filename=Path(source_code).name
        if validate_file_name(runtime,filename):
            sourcecode_location = create_file_with_sourcecode(source_code)
        else:
            return "FAILURE","Please provide valid file.",""
        file_location = upload_file_to_s3(storage_client, bucket, sourcecode_location,function_name)
    else:
        file_location = cloud_storage_location

    # Need a way to be sure upload has completed
    time.sleep(5)

    body = {
        "name": f"projects/{project_name}/locations/{region}/functions/{function_name}",
        "httpsTrigger": {
            "url": f"https://{region}-{project_name}.cloudfunctions.net/{function_name}"
        },
        "status": "ACTIVE",
        "entryPoint": f"{entry_point}",
        "timeout": "60s",
        "availableMemoryMb": int(available_memory_mb),
        "serviceAccountEmail": account_info.get('client_email'),
        "runtime": f"{runtime}",
        "sourceArchiveUrl": f"gs://{file_location}",
    }
    set_progress("Writing file to google cloud function")
    result = client.projects().locations().functions().create(
        location=f"projects/{project_name}/locations/{region}", body=body).execute()

    if result.get('name'):
        generate_custom_fields()
        resource.name = function_name
        resource.google_rh_id = rh.id
        resource.function_name = f"projects/{project_name}/locations/{region}/functions/{function_name}"
        resource.available_memory_mb = available_memory_mb
        resource.entry_point = entry_point
        resource.runtime = runtime
        resource.service_account_email = rh.serviceaccount
        resource.https_trigger = result.get('metadata').get('request').get('httpsTrigger').get('url')
        resource.source_archive_url = result.get('metadata').get('request').get('sourceArchiveUrl')

        resource.save()
        return "SUCCESS", "", ""

    return "FAILURE", "", ""
