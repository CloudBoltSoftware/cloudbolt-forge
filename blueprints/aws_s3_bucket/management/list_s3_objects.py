from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from resources.models import Resource, ResourceType
from infrastructure.models import CustomField


def create_resource_type_if_needed():
    rt, _ = ResourceType.objects.get_or_create(
        name="cloud_file_object",
        defaults={"label": "Cloud File Object", "icon": "far fa-file"}
    )

    CustomField.objects.get_or_create(
        name='s3_file_size', defaults={
            'label': 'File Size', 'type': 'INT', "show_on_servers": True,
            'description': 'Used by Public Cloud File Container BPs'
        }
    )

    CustomField.objects.get_or_create(
        name='s3_file_url', defaults={
            'label': 'Object URL', 'type': 'STR', "show_on_servers": True,
            'description': 'Used by Public Cloud File Container BPs'
        }
    )

    CustomField.objects.get_or_create(
        name='s3_file_uri', defaults={
            'label': 'S3 URI', 'type': 'STR', "show_on_servers": True,
            'description': 'Used by Public Cloud File Container BPs'
        }
    )

    CustomField.objects.get_or_create(
        name='s3_file_last_modified', defaults={
            'label': 'Last Modified', 'type': 'STR', "show_on_servers": True,
            'description': 'Used by Public Cloud File Container BPs'
        }
    )

    return rt


def run(job, resource, **kwargs):
    set_progress("Connecting to AWS s3 cloud")

    aws = AWSHandler.objects.get(id=resource.aws_rh_id)
    set_progress("This resource belongs to {}".format(aws))

    wrapper = aws.get_api_wrapper()
    wrapper.region_name = resource.s3_bucket_region
    
    bucket_name = resource.s3_bucket_name
    
    # get boto3 s3 client object
    client = wrapper.get_boto3_client(
        's3',
        aws.serviceaccount,
        aws.servicepasswd,
        wrapper.region_name
    )

    # get or create resource type
    rt = create_resource_type_if_needed()
    
    # fetch all sub resources
    sub_resources = Resource.objects.filter(parent_resource=resource, resource_type=rt)
    
    added = []
    refreshed = []
    deleted = []
    
    for b_obj in client.list_objects(Bucket=bucket_name).get('Contents', []):
        is_new = False
        name = b_obj['Key']
        
        # filter sub resource by name
        sub_resource = sub_resources.filter(name=name).first()
        
        if sub_resource is None:
            set_progress("Found new cloud file object '{}', creating sub-resource...".format(name))
            
            # create new sub resource
            sub_resource = Resource.objects.create(group=resource.group, parent_resource=resource, resource_type=rt, name=name, 
                            blueprint=resource.blueprint)
            added.append(name)
            is_new = True
        
        sub_resource.lifecycle = "ACTIVE"
        sub_resource.s3_file_size = b_obj['Size']
        sub_resource.s3_file_url = "https://{0}.s3.amazonaws.com/{1}".format(bucket_name, name.replace(" ", "+"))
        sub_resource.s3_file_last_modified = b_obj['LastModified'].strftime("%B %d, %Y, %H:%M:%S(%Z)")
        sub_resource.s3_file_uri = "s3://{0}/{1}".format(bucket_name, name)
        sub_resource.save()
        
        if not is_new:
            set_progress("Refreshing info for '{}'".format(name))
            refreshed.append(name)

    processed = [] + added + refreshed
    
    for f_obj in sub_resources.exclude(name__in=processed):
        
        set_progress("Coudn't find file '{0}' in bucket '{1}', deleting it from CloudBolt...".format(f_obj.name, resource.name))

        f_obj.delete()

    set_progress("Added {} objects, refreshed {} and deleted {}".format(len(added), len(refreshed), len(deleted)))

    return "SUCCESS", "", ""