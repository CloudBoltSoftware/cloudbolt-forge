from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build

from common.methods import set_progress
from infrastructure.models import CustomField, Environment

import json, tempfile
from google.cloud import storage
import os
import zipfile
import time


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
    gce_envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Google Compute Engine")
    options = []
    regions_added = []
    for env in gce_envs:
        region = env.name[:-2]
        if region not in regions_added:
            if region in FUNCTIONS_VALID_REGIONS:
                regions_added.append(region)
                options.append((env.id, region))

    if not options:
        raise RuntimeError("No valid Google Compute Engine resource handlers in CloudBolt")
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
        rh = environment.resource_handler.cast()
        storage_client = create_storage_client(rh)
        buckets = [bucket.name for bucket in storage_client.list_buckets()]

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


def create_storage_client(rh):
    json_fd, json_path = tempfile.mkstemp()

    json_dict = {'client_email': rh.serviceaccount,
                 'token_uri': 'https://www.googleapis.com/oauth2/v4/token',
                 'private_key': rh.servicepasswd
                 }

    with open(json_path, 'w') as fh:
        json.dump(json_dict, fh)

    client = storage.client.Client.from_service_account_json(json_path,
                                                             project=rh.project)

    os.close(json_fd)
    return client


def generate_file_name(runtime):
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
    return runtimes.get(runtime)


def create_file_with_sourcecode(sourcecode, folder, filename):
    # Creates a temporary file containing the sourcecode passed.
    try:
        os.mkdir(f'/tmp/{folder}')
    except Exception as e:
        pass

    with open(f'/tmp/{folder}/{filename}', 'w') as file:
        file.write(sourcecode)

    # Zip the file
    zip_filename = filename.split('.')[0] + '.zip'
    zip_file_location = f'/tmp/{folder}/{zip_filename}'

    zip_ = zipfile.ZipFile(zip_file_location, 'w', zipfile.ZIP_DEFLATED)
    zip_.write(f'/tmp/{folder}/{filename}', arcname=filename)

    return zip_file_location


def upload_file_to_s3(client, bucket_name, file_location):
    bucket = client.get_bucket(bucket_name)
    blob_location = 'functions/' + file_location.split('/')[-2] + file_location.split('/')[-1]
    blob = bucket.blob(blob_location)
    blob.upload_from_filename(file_location)

    return blob_location


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
    rh = environment.resource_handler.cast()

    project = rh.project
    region = environment.name[:-2]

    credentials = ServiceAccountCredentials.from_json_keyfile_dict({
        'client_email': rh.serviceaccount,
        'private_key': rh.servicepasswd,
        'type': 'service_account',
        'project_id': project,
        'client_id': None,
        'private_key_id': None,
    })

    service_name = 'cloudfunctions'
    version = 'v1'
    client = build(service_name, version, credentials=credentials, cache_discovery=False)

    set_progress("Connection to google cloud established")

    # Create a file with an extension corresponding to the runtime selected
    filename = generate_file_name(runtime)
    # We will use seconds as the folder name just to make it unique

    folder = str(time.time()).split('.')[0]

    sourcecode_location = create_file_with_sourcecode(source_code, folder, filename)
    storage_client = create_storage_client(rh)

    if not cloud_storage_location:
        file_location = upload_file_to_s3(storage_client, bucket, sourcecode_location)
    else:
        file_location = cloud_storage_location

    # Need a way to be sure upload has completed
    time.sleep(5)

    body = {
        "name": f"projects/{project}/locations/{region}/functions/{function_name}",
        "httpsTrigger": {
            "url": f"https://{region}-{project}.cloudfunctions.net/{function_name}"
        },
        "status": "ACTIVE",
        "entryPoint": f"{entry_point}",
        "timeout": "60s",
        "availableMemoryMb": int(available_memory_mb),
        "serviceAccountEmail": f"{rh.serviceaccount}",
        "runtime": f"{runtime}",
        "sourceArchiveUrl": f"gs://{bucket}/{file_location}",
    }

    result = client.projects().locations().functions().create(
        location=f"projects/{project}/locations/{region}", body=body).execute()

    if result.get('name'):
        generate_custom_fields()
        resource.name = function_name
        resource.google_rh_id = rh.id
        resource.function_name = f"projects/{project}/locations/{region}/functions/{function_name}"
        resource.available_memory_mb = available_memory_mb
        resource.entry_point = entry_point
        resource.runtime = runtime
        resource.service_account_email = rh.serviceaccount
        resource.https_trigger = result.get('metadata').get('request').get('httpsTrigger').get('url')
        resource.source_archive_url = result.get('metadata').get('request').get('sourceArchiveUrl')

        resource.save()
        return "SUCCESS", "", ""

    return "FAILURE", "", ""
