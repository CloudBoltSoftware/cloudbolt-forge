from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
import boto3

RESOURCE_IDENTIFIER = 'ebs_volume_id'


def discover_resources(**kwargs):
    discovered_volumes = []
    for handler in AWSHandler.objects.all():
        set_progress('Connecting to Amazon EC2 for handler: {}'.format(handler))
        for env in handler.current_regions():
            ec2 = boto3.resource('ec2',
                                 region_name=env,
                                 aws_access_key_id=handler.serviceaccount,
                                 aws_secret_access_key=handler.servicepasswd,
                                 )
            try:
                for volume in ec2.volumes.all():
                    if len(volume.attachments) > 0:
                        instance_id = volume.attachments[0].get('InstanceId')
                        device_name = volume.attachments[0].get('Device')
                    else:
                        instance_id = "N/A"
                        device_name = "N/A"

                    discovered_volumes.append({
                        'name': f"EBS Volume - {volume.volume_id}",
                        'ebs_volume_id': volume.volume_id,
                        "aws_rh_id": handler.id,
                        "aws_region": env,
                        "volume_state": volume.state,
                        "ebs_volume_size": volume.size,
                        "volume_encrypted": volume.encrypted,
                        "instance_id": instance_id,
                        "device_name": device_name,
                    })

            except Exception as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue

    return discovered_volumes
