import json
import pathlib

from django.conf import settings
from django.shortcuts import render

from extensions.views import admin_extension, tab_extension, TabExtensionDelegate
from infrastructure.models import CustomField
from jobs.models import Job
from resourcehandlers.models import ResourceHandler
from resourcehandlers.aws.models import AWSHandler
from utilities.decorators import json_view
from utilities.permissions import cbadmin_required


class AWSResourceHandlerSecurityComplianceTabDelegate(TabExtensionDelegate):
    def should_display(self):
        rh: AWSHandler = self.instance
        cf_queryset = CustomField.objects.filter(
            name=f"aws_security_compliance__{rh.id}"
        )
        return cf_queryset.exists() and isinstance(self.instance.cast(), AWSHandler)


@tab_extension(
    model=ResourceHandler,
    title="Security Hub",
    delegate=AWSResourceHandlerSecurityComplianceTabDelegate,
)
def aws_handler_tab(request, obj_id):
    context = {"rh_id": obj_id}
    return render(
        request, "aws_security_compliance/templates/security_tab.html", context=context
    )


@json_view
def aws_security_compliance_json(request, rh_id):
    """
    Returns AWS Security Hub findings as JSON for a given AWS Resource Handler.
    """
    rh = AWSHandler.objects.get(id=rh_id)
    cf_queryset = CustomField.objects.filter(name=f"aws_security_compliance__{rh.id}")

    if not cf_queryset.exists():
        return []

    cf = cf_queryset.first()
    cfv = cf.customfieldvalue_set.first()
    response = json.loads(cfv.value)

    findings = []
    for finding in response:
        findings.append(
            [
                finding["Title"],
                finding["Description"],
                finding["Region"],
                finding["Severity"]["Product"],
                finding["Compliance"],
                finding["Reference"],
            ]
        )

    return {
        # unaltered from client-side value, but cast to int to avoid XSS
        # http://datatables.net/usage/server-side
        "sEcho": int(request.GET.get("sEcho", 1)),
        "iTotalRecords": 10,
        "iTotalDisplayRecords": 10,
        "aaData": findings,
    }


@admin_extension(
    title="AWS Security Compliance Settings",
    description="Enable/Disable and Schedule the Caching of Security Hub Findings",
)
@cbadmin_required
def aws_security_compliance_config(request):
    """
    View for managing the reccurring job that caches inspector findings
    """
    profile = request.get_user_profile()
    recurring_job = create_recurring_job_if_necessary()

    completed_spawned_jobs = recurring_job.spawned_jobs.filter(
        status__in=Job.COMPLETED_STATUSES
    ).order_by("-start_date")

    if completed_spawned_jobs:
        last_duration = completed_spawned_jobs.first().get_duration()
    else:
        last_duration = "N/A"

    # note: the last job may be queued, pending, or active, so it may not be in past_10_jobs
    last_job = recurring_job.spawned_jobs.last()

    last_success_job = completed_spawned_jobs.filter(status="SUCCESS").first()
    failed_spawned_jobs = completed_spawned_jobs.filter(status="FAILURE")
    last_failed_job = failed_spawned_jobs.first()

    total_count = completed_spawned_jobs.count()
    failure_count = failed_spawned_jobs.count()

    return render(
        request,
        "aws_security_compliance/templates/admin_page.html",
        dict(
            profile=profile,
            recurring_job=recurring_job,
            last_job=last_job,
            last_success_job=last_success_job,
            last_failed_job=last_failed_job,
            last_duration=last_duration,
            total_count=total_count,
            failure_count=failure_count,
        ),
    )


def create_recurring_job_if_necessary():
    recurring_job = {
        "name": "AWS Security Compliance Caching",
        "enabled": True,
        "description": "Fetch Compliance information from AWS Security Hub for each region associated with an AWS Resource Handler.",
        "type": "recurring_action",
        "hook_name": "AWS Security Compliance Caching",
        # once a day at 12:05am
        "schedule": "5 0 * * *",
    }

    recurring_job_hook = {
        "name": recurring_job["name"],
        "description": recurring_job["description"],
        "hook_point": None,
        "module": pathlib.Path(
            settings.PROSERV_DIR,
            "xui/aws_security_compliance/actions/fetch_security_compliance.py",
        ),
    }

    from initialize.create_objects import create_recurring_job, create_hooks
    from cbhooks.models import RecurringActionJob

    create_hooks([recurring_job_hook])
    job = create_recurring_job(recurring_job)
    if not job:
        # this only happens if it already exists
        job = RecurringActionJob.objects.filter(name=recurring_job["name"]).first()

    return job
