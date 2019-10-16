"""
Checks the last hour of AWS Billing Data from S3 buckets, and sends an alert if
any servers have exceeded the specified threshold.

Note: This Action assumes that you have one or more configured Alert Channels
    that can be used for notifying the appropraite users. These channels must
    be listed in ALERT_CHANNEL_NAMES below.

Version:
    Requires >= v9.0.1
"""

import datetime
import json
from typing import List, Tuple

from alerts.methods import alert
from resourcehandlers.aws.models import AWSHandler
from utilities.logger import ThreadLogger

AWS_COST_THRESHOLD = 100
ALERT_CHANNEL_NAMES: List[str] = []

logger = ThreadLogger(__name__)

CostData = Tuple[datetime.datetime, str, float]


class AWSCostAlert:
    def __init__(self):
        self.over_threshold = []

    def __call__(self):
        """
        Retrieve cost data for all AWS Resource Handlers and alert if any
        servers exceed the specified threshold.
        """
        aws_instances = AWSHandler.objects.all()
        for aws in aws_instances:
            last_hours_data = aws.get_yesterday_hourly_billing_data()
            self.__check_threshold(last_hours_data)

        if self.over_threshold:
            _ = self.__alert_over_threshold()

    def __check_threshold(self, data_list):
        """
        Parse server information for instances that exceed the threshold.

        Args:
            data_list (List[CostData]): [(datetime, server_id, cost)]
        """
        _exceed_threshold_list = []
        for time, server_id, cost in data_list:
            if cost >= AWS_COST_THRESHOLD:
                _exceed_threshold_list.append((str(time), server_id, cost))
        self.over_threshold.extend(_exceed_threshold_list)
        return

    def __alert_over_threshold(self):
        """
        Send alert for all server instances that exceed the threshold.

        Returns:
            None
        """
        keys = ["Timestamp", "Resource", "Cost"]
        instance_dict = [dict(zip(keys, i)) for i in self.over_threshold]
        instance_json = json.dumps(instance_dict, indent=4)
        message = (
            f"The following servers exceeded the AWS cost threshold of {AWS_COST_THRESHOLD}:"
            f"{instance_json}"
        )
        logger.info(message)

        for channel_name in ALERT_CHANNEL_NAMES:
            alert(channel_name, message)

        return None


def run(*args, **kwargs):
    cost_alert = AWSCostAlert()
    cost_alert()

    return "SUCCESS", "", ""
