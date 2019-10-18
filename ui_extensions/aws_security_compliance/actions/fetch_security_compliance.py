"""
AWS Security Compliance Action
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

[description]

Requires:
    CloudBolt v9.0
"""

import json

from django.core.serializers.json import DjangoJSONEncoder

# from common.methods import set_progress
from infrastructure.models import CustomField
from orders.models import CustomFieldValue
from resourcehandlers.aws.models import AWSHandler


def _fetch_findings_for_rh(rh: AWSHandler) -> dict:
    """
    [summary]

    Args:
        rh (AWSHandler): [description]

    Returns:
        dict: [description]
    """
    rh_findings: dict = {"Regions": {}}
    regions = set([env.aws_region for env in rh.environment_set.all()])

    for region in regions:
        client = rh.get_boto3_client(service_name="securityhub", region_name=region)
        findings = client.get_findings()["Findings"]
        parsed_findings = _parse_findings(findings)
        rh_findings["Regions"][region] = parsed_findings

    return rh_findings


def _parse_findings(findings: list) -> list:
    """
    [summary]

    Args:
        findings (list): [description]

    Returns:
        list: [description]
    """
    new_findings = []

    for finding in findings:
        new_findings.append(
            {
                "Title": finding["Title"],
                "Description": finding["Description"],
                "Severity": finding["Severity"],
                "Compliance": finding["Compliance"]["Status"],
                "Recommendation": finding["Remediation"]["Recommendation"]["Text"],
                "Reference": finding["Remediation"]["Recommendation"]["Url"],
            }
        )
    return new_findings


def _cache_findings_for_rh(rh: AWSHandler, findings: dict) -> None:
    """
    [summary]

    Args:
        rh (AWSHandler): [description]
        findings (dict): [description]
    """
    json_findings = json.dumps(findings, indent=True, cls=DjangoJSONEncoder)

    cf, _ = CustomField.objects.get_or_create(
        name=f"aws_security_compliance__{rh.name}", label="AWS Security Compliance"
    )
    cf.type = "TXT"
    cf.description = "Do Not Delete: Created by 'AWS Security Compliance' Action."
    cf.save()

    cfv, _ = CustomFieldValue.objects.get_or_create(field=cf)
    cfv.value = json_findings
    cfv.save()

    cf.customfieldvalue_set.add(cfv)
    rh.custom_fields.add(cf)
    rh.save()
    return


def run(*args, **kwargs):
    for rh in AWSHandler.objects.all():
        findings = _fetch_findings_for_rh(rh)
        _cache_findings_for_rh(rh, findings)

    return "", "", ""
