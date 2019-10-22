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

    logger.debug("Parsed scaling config: {}".format(config))
    return config


def run(job, *args, **kwargs):
    """

    :return:
    """
    resources = Resource.objects.filter(
        attributes__field__name="health_check_config",
        lifecycle='ACTIVE'
    )

    for resource in resources:
        config_dict = get_config_value(resource)
        for tier in config_dict.get('tiers', {}):
            name = tier.get('name')
            url = tier.get('url')
            accepted_statuses = tier.get('accepted_statuses')
            timeout_seconds = tier.get('timeout_seconds', 5)

            status_code = None
            retries = 0
            try:
                status_code = requests.get(url, timeout=timeout_seconds).status_code

                if accepted_statuses and status_code not in accepted_statuses:
                    # Bad. TODO: Report this as unavailable
                    # alert
                    job.set_progress(f"HTTP Request returned {status_code}, which is not in the "
                                     f"accepted statuses: {accepted_statuses}.")
                else:
                    # Good. We got a status. No alerting needed.
                    pass

            except Exception as e:
                # Bad, could be ConnectionError, etc.
                job.set_progress(e)
                # need to alert

    return "", "", ""
