from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from resources.models import Resource, ResourceType
from infrastructure.models import CustomField


def create_resource_type_if_needed():
    rt, created = ResourceType.objects.get_or_create(
        name="cloud_file_object",
        defaults={"label": "Cloud File Object", "icon": "far fa-file"}
    )

    cf, _ = CustomField.objects.get_or_create(
        name='cloud_file_obj_size', defaults={
            'label': 'File Size', 'type': 'INT',
            'description': 'Used by Public Cloud File Container BPs'
        }
    )

    if created:
        set_progress("Created Cloud File Object Type")
        rt.list_view_columns.add(cf)

    return rt


def run(job, resource, **kwargs):
    set_progress("Connecting to AWS s3 cloud")

    aws = AWSHandler.objects.get(id=resource.aws_rh_id)
    set_progress("This resource belongs to {}".format(aws))

    wrapper = aws.get_api_wrapper()
    wrapper.region_name = resource.s3_bucket_region
    
    bucket_name = resource.s3_bucket_name
    
    client = wrapper.get_boto3_client(
        's3',
        aws.serviceaccount,
        aws.servicepasswd,
        wrapper.region_name
    )

    rt = create_resource_type_if_needed()
    current_objects = Resource.objects.filter(parent_resource=resource, resource_type=rt)
    added = []
    refreshed = []
    deleted = []
    for b_obj in client.list_objects(Bucket=bucket_name).get('Contents', []):
        is_new = False
        name = b_obj['Key']
        res = current_objects.filter(name=name).first()
        if not res:
            set_progress("Found new cloud file object '{}', creating sub-resource...".format(name))
            res = Resource.objects.create(
                group=resource.group, parent_resource=resource, resource_type=rt, name=name, blueprint=resource.blueprint)
            added.append(name)
            is_new = True
        res.lifecycle = "ACTIVE"
        res.cloud_file_obj_size = b_obj['Size']
        res.save()
        if not is_new:
            set_progress("Refreshing info for '{}'".format(name))
            refreshed.append(name)

    processed = [] + added + refreshed
    for f_obj in current_objects.exclude(name__in=processed):
        set_progress("Coudn't find file '{}' in bucket '{}', deleting it from CloudBolt...".format(
            f_obj.name, resource.name))
        f_obj.delete()
    set_progress("Added {} objects, refreshed {} and deleted {}".format(len(added), len(refreshed), len(deleted)))

    return "SUCCESS", "", ""