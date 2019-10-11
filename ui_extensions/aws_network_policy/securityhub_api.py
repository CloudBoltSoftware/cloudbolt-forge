import json
import django
import settings
import boto3 as boto3

from resourcehandlers.aws.models import AWSHandler

if __name__ == '__main__':
    django.setup()

from infrastructure.models import Server, CustomField
from resourcehandlers.models import ResourceHandler
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


def main():


if __name__ == '__main__':
    main()


def run(job, *args, **kwargs):
    client = boto3.client('securityhub',
                          aws_access_key_id=ACCESS_KEY_ID,
                          aws_secret_access_key=SECRET_ACCESS_KEY,
                          region_name=REGION)

    for rh in AWSHandler.objects.all():
    set_progress('Fetching findings')
    account, instances = fetch_findings(client)
    set_progress('Updating CloudBolt instances')
    update_instances(instances)
    account = group_by_types(account)

    with open(settings.PROSERV_DIR + '/findings.json', 'w') as f:
        json.dump(account, f, indent=True)


    set_progress("This will show up in the job details page in the CB UI, and in the job log")
    server = kwargs.get('server')
    if server:
        set_progress("This plug-in is running for server {}".format(server))

    set_progress("Dictionary of keyword args passed to this plug-in: {}".format(kwargs.items()))

    if True:
        return "SUCCESS", "Sample output message", ""
    else:
        return "FAILURE", "Sample output message", "Sample error message, this is shown in red"
