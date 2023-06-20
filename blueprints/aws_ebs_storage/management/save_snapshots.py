from resourcehandlers.aws.models import AWSHandler
import boto3
from common.methods import set_progress
from servicecatalog.models import ServiceBlueprint
from resources.models import Resource, ResourceType
from accounts.models import Group


def run(job, resource, *args, **kwargs):
    set_progress("Connecting to EC2 EBS")

    volume_id = resource.attributes.get(field__name='ebs_volume_id').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    region = resource.attributes.get(field__name='aws_region').value
    handler = AWSHandler.objects.get(id=rh_id)

    client = boto3.resource('ec2',
                            region_name=region,
                            aws_access_key_id=handler.serviceaccount,
                            aws_secret_access_key=handler.servicepasswd,
                            )

    volume = client.Volume(volume_id)
    snapshot_iterator = volume.snapshots.all()

    blueprint = ServiceBlueprint.objects.filter(name__icontains="snapshots").first()
    group = Group.objects.first()
    resource_type = ResourceType.objects.filter(name__icontains="Snapshot")[0]

    for snap in snapshot_iterator:
        set_progress(snap.state)
        snap.reload()
        res, created = Resource.objects.get_or_create(
            name=snap.id,
            defaults={
                'description': snap.description,
                'blueprint': blueprint,
                'group': group,
                'parent_resource': resource,
                'lifecycle': snap.state,
                'resource_type': resource_type})
        if not created:
            res.description = snap.description
            res.blueprint = blueprint
            res.group = group
            res.parent_resource = resource
            res.lifecycle = snap.state
            res.resource_type = resource_type

            res.save()

    return "SUCCESS", "", ""
