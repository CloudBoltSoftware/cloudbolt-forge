import json

import django
import urllib3

if __name__ == '__main__':
    django.setup()

from infrastructure.models import Server, CustomField
from resourcehandlers.aws.models import AWSHandler
from common.methods import set_progress
from django.core.serializers.json import DjangoJSONEncoder


def fetch_arns_for_findings(inspector_client):
    # at: Assessment template
    # arn: Amazon resource name
    findings = set()

    # Get all assessment templates for current region
    at_arns = inspector_client.list_assessment_templates()['assessmentTemplateArns']
    if len(at_arns) > 0:
        at_details = inspector_client.describe_assessment_templates(assessmentTemplateArns=at_arns)

        # For each template, get the ARN for the latest run
        if "assessmentTemplates" in at_details:
            at_runs = [t['lastAssessmentRunArn'] for t in at_details['assessmentTemplates']]
            paginator = inspector_client.get_paginator('list_findings', )
            for page in paginator.paginate(assessmentRunArns=at_runs,
                                           maxResults=500):
                if len(page['findingArns']) > 0:
                    findings.add(page['findingArns'][0])

    return findings


def get_instance_id(finding):
    for kv in finding['attributes']:
        if kv['key'] == 'INSTANCE_ID':
            return kv['value']
    return None


def update_instances(findings):
    instances = {}

    for finding in findings['findings']:
        instance_id = get_instance_id(finding)
        if instance_id not in instances:
            instances[instance_id] = []
        else:
            instances[instance_id].append(finding)

    for instance in instances.keys():
        try:
            s = Server.objects.get(resource_handler_svr_id=instance)
            cf, _ = CustomField.objects.get_or_create(name='aws_inspector_findings', type='TXT',
                                                      label="AWS Inspector Findings")
            s.set_value_for_custom_field(cf.name, json.dumps(instances[instance], indent=True,
                                                             cls=DjangoJSONEncoder))
        except Server.DoesNotExist as ex:
            # Unable to locate and update the server, carry on
            pass


def describe_findings(inspector_client, all_finding_arns):
    arns = list(all_finding_arns)
    if len(arns) == 0:
        return None
    findings = inspector_client.describe_findings(findingArns=arns)
    return findings


def run(job, *args, **kwargs):
    rh: AWSHandler
    for rh in AWSHandler.objects.all():
        regions = set([env.aws_region for env in rh.environment_set.all()])
        for region in regions:
            inspector = rh.get_boto3_client(service_name='inspector', region_name=region)

            set_progress(f'Fetching findings for {rh.name} ({region}).')
            all_finding_arns = fetch_arns_for_findings(inspector)

            inspector_findings = describe_findings(inspector, all_finding_arns)

            set_progress(f'Updating CloudBolt instances in {region}.')
            if inspector_findings:
                update_instances(inspector_findings)
            # account = group_by_types(account_findings)

            set_progress(f'Updating AWS Account findings for {rh.name}')
            # Next line repeats for each region but is relatively low overhead/impact.
            # with open(settings.PROSERV_DIR + f'/findings-{rh.id}.json', 'w') as f:
            #     json.dump(account, f, indent=True)

    return "", "", ""


if __name__ == '__main__':
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    run(None)
