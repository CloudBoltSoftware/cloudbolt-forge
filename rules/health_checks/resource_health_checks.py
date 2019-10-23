"""
This is a CloudBolt plugin for performing health checks in cloud resources.

This will require some configuration, including..
* Add the 'health_check_config' parameter to any CloudBolt resource
 with Cloud resources you would like to perform health checks on
* Add values for the url to send a request to and the timeout seconds (optional, the default is 5 seconds).
I.e., a valid value for the health check cofig would be the following:
```
{
    'tiers': [
        {
        'name': 'Server01',
        'url': '0.0.0.0',
        'timeout_seconds': 3,
        'accepted_statuses': [200, 201, 418]
        }
    ]
}
```
*

"""
import datetime

from resources.models import Resource
import requests
import json
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
    health_checks = []
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
    )

    check_results = []

    for resource in resources:
        config_dict = get_config_value(resource)
        failure_threshold = config_dict.get('failure_threshold')
        failures = 0

        # Run all the health checks configured for this resource.
        for health_check in config_dict.get('health_checks', {}):
            name = health_check.get('name')
            url = health_check.get('url')
            accepted_statuses = health_check.get('accepted_status_codes')
            timeout_seconds = health_check.get('timeout_seconds', 5)

            retries = 0
            try:
                status_code = requests.get(url, timeout=timeout_seconds).status_code

                if accepted_statuses and status_code not in accepted_statuses:
                    # Bad. TODO: Report this as unavailable
                    # alert
                    job.set_progress(f"HTTP Request returned {status_code}, which is not in the "
                                     f"accepted statuses: {accepted_statuses}.")
                    failures += 1
                else:
                    # Good. We got a status. No alerting needed.
                    continue

            except Exception as e:
                # Bad, could be ConnectionError, which will count as a failure.
                failures += 1
                job.set_progress(e)

            data_dict = {
                'time': datetime.datetime.now(),
                'resource_id': resource.id,
                'resource_name': resource.name,
                'failing_checks': failures,
                'failure_threshold': failure_threshold,
            }

            check_results.append(data_dict)

    context = {
        "health_check_results": check_results,
    }

    # Return the dict to be processed by the "Then" action
    return 'SUCCESS', '', '', {'context': context}


if __name__ == "__main__":
    print(check(None, None))
