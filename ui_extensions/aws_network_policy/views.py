import json
import pathlib

from django.conf import settings
from django.shortcuts import render

from extensions.views import admin_extension, tab_extension, TabExtensionDelegate
from infrastructure.models import Server
from jobs.models import Job
from utilities.decorators import json_view
from utilities.permissions import cbadmin_required

class AWSInspectorServerTabDelegate(TabExtensionDelegate):
    def should_display(self):
        server: Server = self.instance
        return server.get_value_for_custom_field('aws_inspector_findings') is not None


@tab_extension(model=Server, title='Inspector', delegate=AWSInspectorServerTabDelegate)
def server_tab(request, obj_id):
    context = {
        'server_id': obj_id
    }
    return render(request, 'aws_network_policy/templates/server_tab.html', context=context)


@json_view
def aws_network_policy_server_json(request, server_id):
    server = Server.objects.get(id=server_id)
    response = json.loads(server.aws_inspector_findings)
    findings = []

    for finding in response:
        row = [
            finding['title'],
            finding['description'],
            finding['recommendation'],
            finding['severity'],
        ]
        findings.append(row)

    return {
        # unaltered from client-side value, but cast to int to avoid XSS
        # http://datatables.net/usage/server-side
        "sEcho": int(request.GET.get('sEcho', 1)),
        "iTotalRecords": 10,
        "iTotalDisplayRecords": 10,
        'aaData': findings,
    }


@admin_extension(title='AWS Network Policy Settings', description='Enable/Disable and Schedule the Caching of Inspector Findings')
@cbadmin_required
def aws_network_policy_config(request):
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
        last_duration = 'N/A'


    # note: the last job may be queued, pending, or active, so it may not be in past_10_jobs
    last_job = recurring_job.spawned_jobs.last()


    last_success_job = completed_spawned_jobs.filter(status="SUCCESS").first()
    failed_spawned_jobs = completed_spawned_jobs.filter(status="FAILURE")
    last_failed_job = failed_spawned_jobs.first()

    total_count = completed_spawned_jobs.count()
    failure_count = failed_spawned_jobs.count()

    return render(request, 'aws_network_policy/templates/main.html', dict(
        profile=profile,
        recurring_job=recurring_job,
        last_job=last_job,
        last_success_job=last_success_job,
        last_failed_job=last_failed_job,
        last_duration=last_duration,
        total_count=total_count,
        failure_count=failure_count
    ))


def create_recurring_job_if_necessary():
    recurring_job = {
        'name': 'AWS Network Policy Caching',
        'enabled': True,
        'description': 'Create local cached files for aws specific inspector findings',
        'type': 'recurring_action',
        'hook_name': 'AWS Network Policy Caching',
        # once a day at 12:05am
        'schedule': '5 0 * * *',
    }

    recurring_job_hook = {
        'name': 'AWS Network Policy Caching',
        'description': 'Create local cached files for aws specific inspector findings',
        'hook_point': None,
        'module':  pathlib.Path(
            settings.PROSERV_DIR, 'xui/aws_network_policy/actions/fetch_update_findings.py'
        ),
    }

    from initialize.create_objects import create_recurring_job, create_hooks
    from cbhooks.models import RecurringActionJob

    create_hooks([recurring_job_hook])
    job = create_recurring_job(recurring_job)
    if not job:
        # this only happens if it already exists
        job = RecurringActionJob.objects.filter(name=recurring_job['name']).first()

    return job


