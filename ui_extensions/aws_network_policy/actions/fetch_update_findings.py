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
    """
    Fetch all ARNs for findings discovered in the latest run of all enabled Assessment Templates.
    :param inspector_client:
    :return:
    """
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
    """
    Given a finding, go find and return the corresponding AWS Instance ID
    :param finding:
    :return:
    """
    for kv in finding['attributes']:
        if kv['key'] == 'INSTANCE_ID':
            return kv['value']
    return None


def update_instances(findings):
    """
    For each finding build-up a dict keyed by instance ID with an array value of all applicable
    findings. Then create or update the aws_inspector_findings custom field for each
    corresponding CloudBolt server record.
    :param findings:
    :return:
    """
    instances = {}

    # Group findings by instance
    for finding in findings['findings']:
        instance_id = get_instance_id(finding)
        if instance_id not in instances:
            instances[instance_id] = []
        else:
            instances[instance_id].append(finding)

    # For each istance, find its CloudBolt Server record and update aws_inspector_findings
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
    """
    Given a list of findind ARNs, return the details for each finding.
    :param inspector_client:
    :param all_finding_arns:
    :return:
    """
    arns = list(all_finding_arns)
    if len(arns) == 0:
        return None
    findings = inspector_client.describe_findings(findingArns=arns)
    return findings


def run(job, *args, **kwargs):
    rh: AWSHandler
    for rh in AWSHandler.objects.all():
        regions = set([env.aws_region for env in rh.environment_set.all()])
        # For each region currently used by the current AWSHandler
        for region in regions:
            inspector = rh.get_boto3_client(service_name='inspector', region_name=region)

            set_progress(f'Fetching findings for {rh.name} ({region}).')
            all_finding_arns = fetch_arns_for_findings(inspector)

            inspector_findings = describe_findings(inspector, all_finding_arns)

            set_progress(f'Updating CloudBolt instances in {region}.')
            if inspector_findings:
                update_instances(inspector_findings)

    return "", "", ""


if __name__ == '__main__':
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    run(None)
