import json
import django
import settings
import boto3 as boto3

if __name__ == '__main__':
    django.setup()

from resourcehandlers.aws.models import AWSHandler
from infrastructure.models import Server, CustomField
from common.methods import set_progress


def fetch_findings(sh_client):
    paginator = sh_client.get_paginator('get_findings')
    finding_iterator = paginator.paginate(PaginationConfig={'PageSize': 25})

    curr_page = 0
    instances = {}
    account = []

    for page in finding_iterator:
        for f in page['Findings']:
            instance_id = get_instance_id(f)
            resource_type = get_resource_type(f)
            if resource_type == 'AwsEc2Instance':
                if instance_id not in instances.keys():
                    instances[instance_id] = []
                instances[instance_id].append(f)
            elif resource_type == 'AwsAccount':
                account.append(f)
        curr_page += 1

    return account, instances


def get_resource_type(finding):
    return finding['Resources'][0]['Type']


def get_instance_id(finding):
    for k in finding['ProductFields'].keys():
        if finding['ProductFields'][k] == 'INSTANCE_ID':
            key = k.replace('/key', '/value')
            return finding['ProductFields'][key]


def update_instances(instances):
    for i in instances:
        s = Server.objects.get(resource_handler_svr_id=i)
        cf, _ = CustomField.objects.get_or_create(name='aws_securityhub_findings', type='TXT',
                                                  label="AWS SecurityHub Findings")
        s.set_value_for_custom_field(cf.name, json.dumps(instances[i], indent=True))


def group_by_types(account):
    grouped_findings = dict()
    for f in account:
        finding_type = f['Types'][0]
        if finding_type not in grouped_findings:
            grouped_findings[finding_type] = []
        grouped_findings[finding_type].append(f)
        grouped_findings[finding_type] = sorted(grouped_findings[finding_type], key=lambda v: v['Title'])

    return grouped_findings


def run(job, *args, **kwargs):
    rh: AWSHandler
    for rh in AWSHandler.objects.all():
        regions = set([env.aws_region for env in rh.environment_set.all()])
        for region in regions:
            set_progress(f'Fetching findings for {rh.name} ({region}).')
            client = rh.get_boto3_client(service_name='securityhub', region_name=region)
            # Fetch account-level and instance-level findings for the current region. Note: account-level findings
            # span all regions.
            account, instances = fetch_findings(client)
            set_progress(f'Updating CloudBolt instances in {region}.')
            update_instances(instances)
            account = group_by_types(account)
            set_progress(f'Updating AWS Account findings for {rh.name}')
            # Next line repeats for each region but is relatively low overhead/impact.
            with open(settings.PROSERV_DIR + f'/findings-{rh.id}.json', 'w') as f:
                json.dump(account, f, indent=True)

    return "", "", ""


if __name__ == '__main__':
    run(None)
