import json
import os
from pprint import pformat

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from extensions.views import tab_extension, TabExtensionDelegate
from jobs.models import RecurringJob
from resourcehandlers.aws.models import AWSHandler
from resourcehandlers.models import ResourceHandler
from utilities.views import dialog_view, redirect_to_referrer

from .forms import AWSIAMPolicyForm
from .iam_policy_utilities import IAM_POLICY_CACHE_LOCATION_PATH, get_iam_policies, get_iam_policy_details


@tab_extension(model=ResourceHandler, title='IAM Policies')
def awshandler_iam_policies_tab(request, obj_id):
    handler = AWSHandler.objects.get(id=obj_id)
    job = RecurringJob.objects.filter(name="AWS IAM Policy Caching").first()
    if not job:
        print('Creating the Recurring Job')
        from .iam_policy_utilities import setup_aws_iam_policies
        setup_aws_iam_policies()

    # first look for cached data, else try to fetch it realtime
    policies = get_iam_policies_from_cache(handler.id)
    if not policies:
        print('Unable to load policies from cache')
        policies = get_iam_policies(handler)

    context = {
        "handler": handler,
        "policies": policies,
        "column_headings": ['Name', 'Arn', 'Path'],
    }

    return render(request, 'iam_policies/templates/policy_list.html', context)


@dialog_view(template_name='iam_policies/templates/policy_detail.html')
def aws_iam_policy_detail(request, handler_id, policy_arn, policy_name):
    """
    We make an API call to fetch the policy details each time this detail view
    is hit, as we aren't storing the JSON policy documents in the filesystem.
    """
    handler = AWSHandler.objects.get(id=handler_id)
    policy_details = get_iam_policy_details(handler, policy_arn)
    policy_document = pformat(policy_details['PolicyVersion']['Document'])   

    return {
        "title": "IAM Policy Details",
        "handler": handler,
        "policy_arn": policy_arn,
        "policy_document": policy_document,
        "policy_name": policy_name,
    }


def discover_aws_iam_policies(request, handler_id):
    handler = AWSHandler.objects.get(id=handler_id)
    get_iam_policies(handler)
    return redirect_to_referrer(request, default_url=reverse('resourcehandler_detail', args=[handler_id]))


@dialog_view
def add_aws_iam_policy(request, handler_id):
    handler = AWSHandler.objects.get(id=handler_id)

    if request.method == 'POST':
        form = AWSIAMPolicyForm(request.POST, handler=handler)
        if form.is_valid():
            success, msg = form.save()
            if success:
                messages.success(request, msg)
            else:
                messages.warning(request, msg)
            return HttpResponseRedirect(reverse('resourcehandler_detail', args=[handler_id]))

    else:
        form = AWSIAMPolicyForm(handler=handler)

    return {
        'use_ajax': True,
        'form': form,
        'title': 'Add AWS IAM Policy',
        'action_url': '/{}/aws_iam_policy/add/'.format(handler_id),
        'submit': 'Add'
    }


def get_iam_policies_from_cache(handler_id):

    try:
        path = os.path.join(IAM_POLICY_CACHE_LOCATION_PATH, 'handler-{}-policies.json'.format(handler_id))
        cached_policy_list = json.load(open(path))
    except Exception:
        # we could catch specific exceptions but they'd all result in the same,
        # trying to fetch real time data
        cached_policy_list = None

    return cached_policy_list
