from resourcehandlers.aws.models import AWSHandler
import boto3
import time
from common.methods import set_progress


def run(job, resource, *args, **kwargs):
    handler = AWSHandler.objects.get(id=resource.aws_rh_id)
    volume_id = resource.attributes.get(field__name='ebs_volume_id').value
    region = resource.attributes.get(field__name='aws_region').value

    device = resource.device_name
    instance_id = resource.instance_id

    ec2 = boto3.resource('ec2',
                         region_name=region,
                         aws_access_key_id=handler.serviceaccount,
                         aws_secret_access_key=handler.servicepasswd,
                         )
    volume = ec2.Volume(volume_id)

    state = volume.state
    if state.lower() != 'in-use':
        return "FAILURE", f"Can not detach volume from instance since the volume is in '{state.upper()}' state", ""

    try:
        response = volume.detach_from_instance(
            Device=device,
            InstanceId=instance_id,
        )
        # wait until the detachment process is complete
        count = 0
        while state != 'available':
            set_progress(f"Detaching Instance...")
            count += 5
            time.sleep(5)
            volume.reload()
            state = volume.state

            if count > 3600:
                # Detaching is taking too long
                return "FAILURE", "Failed to detach volume from instance", "Detachment taking too long."

        resource.instance_id = "N/A"
        resource.device_name = "N/A"
        resource.volume_state = volume.state
        resource.save()

    except Exception as e:
        return "FAILURE", "Failed to attach volume to instance", f"{e}"
    return "SUCCESS", "", ""
