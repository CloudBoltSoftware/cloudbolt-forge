import json

import django

import settings

if __name__ == '__main__':
    django.setup()

import boto3 as boto3

from infrastructure.models import Server, CustomField

ACCESS_KEY_ID = "AKIAID5LHCP3V7I4CMHA"
SECRET_ACCESS_KEY = "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"
REGION = "us-west-1"


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


def main():
    client = boto3.client('securityhub',
                          aws_access_key_id=ACCESS_KEY_ID,
                          aws_secret_access_key=SECRET_ACCESS_KEY,
                          region_name=REGION)
    print('Fetching findings')
    account, instances = fetch_findings(client)
    print('Updating CloudBolt instances')
    update_instances(instances)
    with open(settings.PROSERV_DIR + '/findings.json', 'w') as f:
        json.dump(account, f, indent=True)


if __name__ == '__main__':
    main()
