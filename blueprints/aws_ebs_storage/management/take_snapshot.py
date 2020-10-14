from resourcehandlers.aws.models import AWSHandler
import boto3
import time
from common.methods import set_progress
from servicecatalog.models import ServiceBlueprint
from resources.models import Resource, ResourceType
from accounts.models import Group


def run(resource, *args, **kwargs):
    set_progress("Connecting to EC2")
    handler = AWSHandler.objects.get(id=resource.aws_rh_id)
    set_progress("This resource belongs to {}".format(handler))

    volume_id = resource.attributes.get(field__name='ebs_volume_id').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    region = resource.attributes.get(field__name='aws_region').value
    handler = AWSHandler.objects.get(id=rh_id)
    blueprint = ServiceBlueprint.objects.filter(name__icontains="snapshots").first()
    group = Group.objects.first()
    resource_type = ResourceType.objects.filter(name__icontains="Snapshot")[0]

    ec2 = boto3.resource('ec2',
                region_name=region,
                aws_access_key_id=handler.serviceaccount,
                aws_secret_access_key=handler.servicepasswd,
            )
    volume = ec2.Volume(volume_id)

    snapshot = volume.create_snapshot(
        Description='Volume Snapshot for {}'.format(volume_id),
    )
    state = snapshot.state
    count = 0
    while state !='completed':
        set_progress(f"Creating snapshot...")
        count +=5
        time.sleep(5)
        snapshot.reload()
        state = snapshot.state
        if count > 3600:
            # Taking snapshot os taking too long
            return "FAILURE", "Failed to take a snapshot", "Snapshot taking took too long."

    # Save the snapshot to the list of available snapshots
    Resource.objects.get_or_create(
        name=snapshot.id,
        defaults={
            'description': snapshot.description,
            'blueprint': blueprint,
            'group': group,
            'parent_resource': resource,
            'lifecycle': snapshot.state,
            'resource_type': resource_type})
    return "SUCCESS", "", ""
