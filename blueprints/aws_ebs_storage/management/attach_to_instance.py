from common.methods import set_progress
import boto3
import time
from botocore.client import ClientError
from infrastructure.models import Environment
from resources.models import Resource
from resourcehandlers.aws.models import AWSHandler


def generate_options_for_instances(resource, **kwargs):
    instances = []
    rh = AWSHandler.objects.get(id=resource.aws_rh_id)

    region = resource.aws_region

    ec2 = boto3.client(
        'ec2',
        region_name=region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )
    response = ec2.describe_instances()['Reservations']
    for instance in response:
        res = instance['Instances'][0]
        instances.append(res.get('InstanceId'))
    return instances


def run(job, *args, **kwargs):
    resource = kwargs.get('resources').first()

    instance_id = "{{ instances }}"
    device = "{{ device }}"

    volume_id = resource.attributes.get(field__name='ebs_volume_id').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    region = resource.attributes.get(field__name='aws_region').value
    handler = AWSHandler.objects.get(id=rh_id)

    ec2 = boto3.resource('ec2',
                         region_name=region,
                         aws_access_key_id=handler.serviceaccount,
                         aws_secret_access_key=handler.servicepasswd,
                         )

    volume = ec2.Volume(volume_id)

    state = volume.state
    if state != 'available':
        return "FAILURE", f"Can not attach volume to instance since the volume is in '{state.upper()}' state", ""

    set_progress("Connecting to Amazon EC2...")

    try:
        response = volume.attach_to_instance(
            Device=device,
            InstanceId=instance_id
        )
        # wait until the attachment process is complete
        state = response.get('State')
        count = 0
        while state == 'attaching':
            set_progress("Attaching Instance")
            count += 5
            time.sleep(5)
            state = volume.attachments[0].get('State')
            if count > 3600:
                # Attaching is taking too long
                return "FAILURE", "Failed to attach volume to instance", "Attachment taking too long."
        resource.instance_id = instance_id
        resource.device_name = device
        resource.volume_state = volume.state
        resource.save()

    except ClientError as e:
        return "FAILURE", "Failed to attach volume to instance", f"{e}"

    return "SUCCESS", f"Volume {volume_id} has been successfully attached", ""
