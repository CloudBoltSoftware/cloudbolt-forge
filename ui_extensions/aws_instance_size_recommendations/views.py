# This Python file uses the following encoding: utf-8
# The above line is required to support the use of unicode characters below.
from django.shortcuts import render, get_object_or_404
from django.utils.safestring import mark_safe

from extensions.views import tab_extension, TabExtensionDelegate
from resourcehandlers.aws.models import AWSHandler
from resourcehandlers.models import ResourceHandler
from typing import Dict

from utilities.exceptions import CloudBoltException
from utilities.logger import ThreadLogger
from botocore.exceptions import UnknownServiceError

logger = ThreadLogger(__name__)


class AWSTabDelegate(TabExtensionDelegate):

    def should_display(self):
        return isinstance(self.instance.cast(), AWSHandler)


def get_recommendation_dict(raw_dict):
    """
    Extract the attributes that we care about for a rightsizing recommendation
    and build a new dict that will be more readable and more simple for use in the
    template context.

    :param raw_dict: The original dictionary from the API response
    :return: a much cleaner, filtered down dict of info for the template context.
    """
    current_instance = raw_dict.get('CurrentInstance')

    # Only process EC2 instances. (at least for now...)
    ec2_details = current_instance.get(
        'ResourceDetails').get(
        'EC2ResourceDetails')
    curr_instance_type = ec2_details.get('InstanceType')
    curr_instance_region = ec2_details.get('Region')
    resource_utilization = current_instance.get(
        'ResourceUtilization').get(
        'EC2ResourceUtilization'
    )

    # Build a recommendation summary to tell the user what is being recommended.
    rec_type = raw_dict.get('RightsizingType')  # 'Terminate'|'Modify'
    if rec_type == 'Terminate':
        details = raw_dict.get('TerminateRecommendationDetail')  # type: Dict
        savings = details.get('EstimatedMonthlySavings')
        currency = details.get('CurrencyCode')
        target_utilization = None
        action_msg = mark_safe(f"Terminate instance")
    else:
        # rec_type = 'Modify'
        target_instances = raw_dict.get('ModifyRecommendationDetail').get('TargetInstances')  # type: list
        # Pick the instance type with the most savings and use that one.
        target_instances = sorted(
            target_instances,
            key=lambda x: x['EstimatedMonthlySavings'],
            reverse=True
        )
        new_instance = target_instances[0]
        target_ec2_details = new_instance.get('ResourceDetails').get('EC2ResourceDetails')
        target_utilization_response = new_instance.get('ExpectedResourceUtilization').get('EC2ResourceUtilization')
        target_utilization = {
            'CPU': target_utilization_response.get('MaxCpuUtilizationPercentage'),
            'Mem': target_utilization_response.get('MaxMemoryUtilizationPercentage'),
            'Stor': target_utilization_response.get('MaxStorageUtilizationPercentage'),
        }
        savings = new_instance.get('EstimatedMonthlySavings')
        currency = new_instance.get('CurrencyCode')
        new_instance_type = target_ec2_details.get('InstanceType')
        action_msg = mark_safe("Change this instance type to <b>{new_instance_type}</b>".format(
            new_instance_type=new_instance_type
        ))

    savings = round(float(savings), 2)
    action_msg += mark_safe(' to save an estimated <b>{savings} {currency}</b> per month.'.format(
        savings=savings,
        currency=currency
    ))

    recommendation_dict = {
        'current_instance': {
            'id': current_instance.get('ResourceId'),
            'instance_type': curr_instance_type,
            'region': curr_instance_region,
            'monthly_cost': current_instance.get('MonthlyCost'),
            'currency': current_instance.get('CurrencyCode'),
            'utilization_percent': {
                'CPU':  resource_utilization.get('MaxCpuUtilizationPercentage'),
                'Mem': resource_utilization.get('MaxMemoryUtilizationPercentage'),
                'Stor': resource_utilization.get('MaxStorageUtilizationPercentage'),
            }
        },
        'recommendations': {
            'type': rec_type,
            'savings': savings,
            'action': action_msg,
            'utilization_percent': target_utilization
        }
    }

    return recommendation_dict


def get_recommended_server_instance_types(handler: AWSHandler):
    """
    Connect to the boto3 CostExplorer client and get recommended
    instance sizes for all ec2 instances on this account with info
    about potential cost savings.
    """

    wrapper = handler.get_api_wrapper()

    recommendations_by_instance = dict()
    total_savings = 0

    client = wrapper.get_boto3_client(
        'ce',
        handler.serviceaccount,
        handler.servicepasswd,
        'us-east-1'  # Connecting to any region should return recommendations for all regions.
    )

    try:
        response = client.get_rightsizing_recommendation(Service='AmazonEC2')
    except (AttributeError, UnknownServiceError):
        # This will happen if the version of boto3 pre-dates the existence
        # of either this CostExplorer method that is being called, or the CostExplorer
        # Service all together. If this happens, then let the
        # user know what version of CloudBolt they need to be on for this to work.
        raise CloudBoltException(
            'This version of CloudBolt does not support '
            'this UI-extension. Please upgrade to version 9.0.1 or '
            'greater to get recommendations. '
        )

    summary_data = response.get('Summary')
    total_recommendations = int(summary_data.get('TotalRecommendationCount'))

    if total_recommendations > 0:
        recommendations_list = response.get('RightsizingRecommendations')

        # Save all the recommendations for this region.
        for raw_dict in recommendations_list:
            recommendation_dict = get_recommendation_dict(raw_dict)
            instance_id = recommendation_dict.get('current_instance').get('id')
            recommendations_by_instance[instance_id] = recommendation_dict
            total_savings += float(recommendation_dict.get('recommendations').get('savings'))

    currency = summary_data.get('SavingsCurrencyCode')
    summary = dict(
        total_recommendations=total_recommendations,
        total_savings=total_savings,
        currency=currency
    )

    return recommendations_by_instance, summary


@tab_extension(model=ResourceHandler, title='Instance Type Recommendations', delegate=AWSTabDelegate)
def size_recommendation_tab(request, obj_id):
    """
    Render the tab with all of the recommended server instance types that exist.

    """

    resource_handler = get_object_or_404(ResourceHandler, pk=obj_id).cast()

    try:
        recommendations_by_instance, summary = \
            get_recommended_server_instance_types(resource_handler)
        context = dict(
            error=None,
            resource_handler=resource_handler,
            recommendations=recommendations_by_instance,
            summary=summary
        )
    except CloudBoltException as e:
        context = dict(error=e)

    # Prepare your data
    # The path to your template must include the extension package name,
    # here "hello_world_dashboard_ext".
    return render(
        request,
        'aws_instance_size_recommendations/templates/tab_instance_type_recommendations.html',
        context
    )
