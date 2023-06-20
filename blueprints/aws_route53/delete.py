from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler


def run(job, *args, **kwargs):
    resource = kwargs.pop('resources').first()

    rh_id = resource.aws_rh_id
    rh = AWSHandler.objects.get(id=rh_id)
    try:
        wrapper = rh.get_api_wrapper()
    except Exception:
        return
    name = resource.name
    record_type = resource.dns_record_type
    zone_id = resource.zone_id

    set_progress("Connecting to AWS Route53...")

    client = wrapper.get_boto3_client(
        'route53',
        rh.serviceaccount,
        rh.servicepasswd,
        None
    )

    # fetch the record to make sure we have the correct data to pass
    record = client.list_resource_record_sets(
        HostedZoneId=zone_id, StartRecordName=name, StartRecordType=record_type, MaxItems='1'
    )['ResourceRecordSets'][0]

    batch = {
        'Changes': [
            {
                'Action': "DELETE",
                'ResourceRecordSet': record
            },
        ]
    }

    client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch=batch
    )

    return "SUCCESS", "The record has been successfully deleted", ""
