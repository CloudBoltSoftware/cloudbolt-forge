from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler

import boto3
import time


def run(job, *args, **kwargs):
    resource = kwargs.pop('resources').first()
    rh_id = resource.aws_rh_id
    rh = AWSHandler.objects.get(id=rh_id)

    fsx = boto3.client(
        'fsx',
        region_name=resource.aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )
    fsx.delete_file_system(FileSystemId=resource.name)

    # Wait for the file system to be fully deleted
    def get_lifecycle():
        try:
            res = fsx.describe_file_systems(FileSystemIds=[resource.name])

            lifecycle = res.get('FileSystems')[0].get('Lifecycle')
        except Exception as e:
            # Once the file system has been deleted,
            # an exception will be raised while trying to describe that file system.
            lifecycle = "DELETED"

        return lifecycle

    lifecycle = get_lifecycle()

    while lifecycle == "DELETING":
        set_progress(f"File System Status: {lifecycle}")
        time.sleep(60)
        lifecycle = get_lifecycle()

    if lifecycle == "DELETED":
        return "SUCCESS", f"{resource.name} Deleted Successfully", ""
    else:
        return "FAILURE", "Failed to delete file system", f"File System Status is {lifecycle}"
