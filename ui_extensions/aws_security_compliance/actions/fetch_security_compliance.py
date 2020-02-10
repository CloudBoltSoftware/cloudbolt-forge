"""
AWS Security Compliance Action
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch Compliance information from AWS Security Hub for each region associated
with an AWS Resource Handler.

Note:
    Configure this action to run as a Recurring Job to regularly fetch AWS
    Security Compliance information.

Requires:
    CloudBolt v9.0
"""

import json

from django.core.serializers.json import DjangoJSONEncoder

from common.methods import set_progress
from infrastructure.models import CustomField
from orders.models import CustomFieldValue
from resourcehandlers.aws.models import AWSHandler


def _fetch_findings_for_rh(rh):
    """
    Return list of Security Hub compliance findings for a given AWS Resource
    Handler.

    Args:
        rh (AWSHandler): AWS Resource Handler.

    Returns:
        List[dict]: List of compliance information dictionaries.
    """
    rh_findings: list = []
    regions = set([env.aws_region for env in rh.environment_set.all()])

    for region in regions:
        client = rh.get_boto3_client(service_name="securityhub", region_name=region)
        findings = client.get_findings()["Findings"]
        parsed_findings = _parse_findings(findings, region)
        rh_findings += parsed_findings

    return rh_findings


def _parse_findings(findings, region):
    """
    Returns relevant information from AWS Security Hub API response.

    Args:
        findings (list): AWS Security Hub response.
        region (str): AWS region.

    Returns:
        List[dict]: List of compliance information dictionaries.
    """
    new_findings = []

    for finding in findings:
        new_findings.append(
            {
                "Region": region,
                "Title": finding["Title"],
                "Description": finding["Description"],
                "Severity": finding["Severity"],
                "Compliance": finding["Compliance"]["Status"],
                "Recommendation": finding["Remediation"]["Recommendation"]["Text"],
                "Reference": finding["Remediation"]["Recommendation"]["Url"],
            }
        )
    return new_findings


def _cache_findings_for_rh(rh, findings):
    """
    Saves Security Hub compliance findings for a given AWS Resource Handler for
    later access.

    Args:
        rh (AWSHandler): AWS Resource Handler.
        findings (List[dict]): List of compliance information dictionaries.
    """
    json_findings = json.dumps(findings, indent=True, cls=DjangoJSONEncoder)

    cf, _ = CustomField.objects.get_or_create(
        name=f"aws_security_compliance__{rh.id}", label="AWS Security Compliance"
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
    set_progress(
        f"Downloading AWS Security Compliance data for {AWSHandler.objects.count()} "
        f"AWS Resource Handler(s)."
    )
    for rh in AWSHandler.objects.all():
        findings = _fetch_findings_for_rh(rh)
        _cache_findings_for_rh(rh, findings)

    return "", "", ""
