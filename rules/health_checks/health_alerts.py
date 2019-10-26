"""
Uses the results of the Resource Health Checks condition to alert users
if any resources have health check failures exceeding their threshold for failures.
See health_checks/README.md for more setup instructions for the rule this plugin runs in.

Note: This Action assumes that you have one or more configured Alert Channels
    that can be used for notifying the appropraite users. These channels must
    be listed in ALERT_CHANNEL_NAMES below.

CloudBolt Version:
    Requires >= v9.0.1
"""

import json
import sys
from typing import List

from alerts.methods import alert
from common.methods import set_progress
from jobs.models import Job
from utilities.logger import ThreadLogger

ALERT_CHANNEL_NAMES: List[str] = []

logger = ThreadLogger(__name__)


class ResourceHealthAlert:
    def __init__(self, context):
        self.health_stats = context['health_check_results']
        self.over_threshold = []

    def __call__(self):
        """
        Iterate over all health stats for resources and check whether
        there were over-threshold failures to alert on, save them and alert if so.
        """

        for result_dict in self.health_stats:
            self.__check_threshold(result_dict)

        if self.over_threshold:
            self.__alert_over_threshold()

    def __check_threshold(self, result_dict):
        """
        Checks whether the given resource had over-threshold number of
        failures and stores it if so.
        """

        time = result_dict.get('time')
        failing_checks = result_dict.get('failing_checks', 0)
        resource_name = result_dict.get('resource_name')
        resource_id = result_dict.get('resource_id')

        if failing_checks:
            self.over_threshold.append((str(time), resource_name, resource_id, failing_checks))

        return

    def __alert_over_threshold(self):
        """
        Send alert for all resource health checks that exceed the threshold.
        """
        keys = ["Timestamp", "Resource", "ID", "Failing Checks"]
        instance_dict = [dict(zip(keys, i)) for i in self.over_threshold]
        instance_json = json.dumps(instance_dict, indent=4)
        message = (
            f"The following resources exceeded their health check failure threshold:"
            f"{instance_json}"
        )
        set_progress(message)

        for _channel_name in ALERT_CHANNEL_NAMES:
            alert("health_check", message)

        return None


def run(job, logger):
    params = job.job_parameters.cast().arguments
    context = params.get('context')

    health_alert = ResourceHealthAlert(context)
    health_alert()

    return "SUCCESS", "", ""


if __name__ == "__main__":
    print(run(job=Job.objects.get(id=sys.argv[1]), logger=logger))
