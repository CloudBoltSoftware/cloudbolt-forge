"""
This is a CloudBolt plugin for performing health checks in cloud resources.

This will require some configuration, including..
* Add the 'health_check_config' parameter to any CloudBolt resource
 with Cloud resources you would like to perform health checks on
* Add values for the url to send a request to and the timeout seconds (optional, the default is 5 seconds).
I.e., a valid value for the health check config would be the following:
```
{
    "health_checks": [
        {
        "name": "Teapot",
        "url": "0.0.0.0",
        "timeout_seconds": 3,
        "accepted_statuses": [418]
        }
    ]
}

Read more instructions for setting up this rule in health_checks/README.md
```
*

"""
import datetime
import json
import time

import requests
import sys

from common.methods import set_progress
from jobs.models import Job
from resources.models import Resource
from utilities.logger import ThreadLogger


logger = ThreadLogger(__name__)


def get_config_value(resource):
    health_check_config = resource.attributes.get(field__name="health_check_config").value
    try:
        config = json.loads(health_check_config)
    except Exception:
        logger.debug('Error parsing health check config: {}'.format(health_check_config))
        raise

    # Check for required parameters here.
    try:
        health_checks = config['health_checks']
        name = health_checks[0]['name']
        url = health_checks[0]['url']
    except (KeyError, IndexError):
        logger.debug("Error parsing health check config, missing required parameter(s).")
        raise

    logger.debug("Parsed scaling config: {}".format(config))
    return config


def check(job, logger, **kwargs):
    """
    Run health checks for all active resources with the health_check_config parameter set.
    If the number of failing checks exceed the threshold for failure for a given resource,
    compile that into a report for the alerting action to run after this plugin.
    """
    resources = Resource.objects.filter(
        attributes__field__name="health_check_config",
        lifecycle='ACTIVE'
    ).distinct()
    set_progress(
        f"Will run health checks for {resources.count()} resource(s): "
        f"{[resource.name for resource in resources]}")

    check_results = []

    for resource in resources:
        logger.info(f"Will run health checks for resource '{resource.name}'.")
        config_dict = get_config_value(resource)
        failing_health_checks = 0

        # Run all the health checks configured for this resource.
        for health_check in config_dict.get('health_checks', {}):
            max_retries = health_check.get('max_retries', 3)
            retry_interval_seconds = health_check.get('retry_interval_seconds', 1)

            name = health_check.get('name')
            job.set_progress(f"Beginning health check '{name}'.")
            url = health_check.get('url')
            accepted_statuses = health_check.get('accepted_status_codes')
            timeout_seconds = health_check.get('timeout_seconds', 3)

            retry_attempts = 0
            while retry_attempts <= max_retries:
                try:
                    if retry_attempts > 1:
                        logger.info(f"On retry attempt {retry_attempts}.")
                    status_code = requests.get(url, timeout=timeout_seconds).status_code

                    if accepted_statuses and status_code not in accepted_statuses:
                        # Failure.
                        msg = (
                            f"HTTP Request returned {status_code}, "
                            f"which is not in the accepted statuses: {accepted_statuses}"
                            f"for health check '{name}'."
                        )
                        logger.debug(msg)
                        retry_attempts += 1
                    else:
                        # Pass - We got a valid status. We can stop now.
                        logger.info(f"Health check '{name}' completed with success.")
                        break

                except Exception as e:
                    # Bad, could be ConnectionError, which will count as a failure.
                    logger.debug(e)
                    retry_attempts += 1

                # Wait for the specified retry interval before trying again
                time.sleep(retry_interval_seconds)

            if retry_attempts == max_retries:
                job.set_progress(f"Max retries exceeded for health check '{name}'.")
                failing_health_checks += 1

        # Summarize this resource's health check results.
        data_dict = {
            'time': datetime.datetime.now(),
            'resource_id': resource.id,
            'resource_name': resource.name,
            'failing_health_checks': failing_health_checks,
        }

        check_results.append(data_dict)

    context = {
        "health_check_results": check_results,
    }

    # Return the dict to be processed by the "Then" action
    return 'SUCCESS', '', '', {'context': context}


if __name__ == "__main__":
    print(check(job=Job.objects.get(id=sys.argv[1]), logger=logger))
