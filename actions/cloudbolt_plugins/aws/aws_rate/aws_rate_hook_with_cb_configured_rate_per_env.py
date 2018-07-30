"""
Calculates the on-demand rate for the chosen AWS instance type and CB Admin defined rate for Software, Parameter and Application per environment.
Enable this hook to see your own defined rate per environment along with on-demand rate for AWS instance type in order form cost breakdown.

Rate is displayed in the time units chosen in Rates Options. Assumes the
currency is USD, edit this action to change it.

This file is applied when provisioning a server.
These rates are updated regularly by the 'Refresh Server Rates' recurring job.
"""


from decimal import Decimal
import os.path
import ijson
import json
import re
import requests

from django.conf import settings
from django.core.cache import cache

from resourcehandlers.aws.models import AWSHandler, get_region_title
from utilities.filesystem import mkdir_p
from utilities.logger import ThreadLogger
from utilities.models import GlobalPreferences
from costs.utils import default_compute_rate

NUMBER_OF_HOURS = {
    "HOUR": 1,
    "DAY": 24,
    "WEEK": 192,
    "MONTH": 720,  # assumes 30-day month
    "YEAR": 8760,  # assumes 365-day year
}

RATE_HOOK_DIR = "{}/opt/cloudbolt/aws_rate_hook".format(settings.VARDIR)
AWS_URL = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.json"
logger = ThreadLogger(__name__)


def download_file(url, file_location):
    """
    Downloads the pricing file if it does not already exist.
    """
    if os.path.exists(file_location):
        return

    # try making the directory to store rate files in.
    mkdir_p(RATE_HOOK_DIR)

    logger.debug('Downloading AWS pricing file from {}'.format(url))
    r = requests.get(url, stream=True)
    with open(file_location, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
    logger.debug('Download complete')


def split_file(file_location, products_file, terms_file):
    """
    Splits file into two components for faster lookups.

    products_file contains SKUs for each location/instance type combination.
    terms_file contains the on-demand pricing for each SKU.
    """
    if os.path.exists(products_file) and os.path.exists(terms_file):
        return
    logger.debug('Splitting AWS pricing file')
    with open(file_location) as f:
        full_data = json.load(f)
    with open(products_file, 'w') as f:
        json.dump(full_data['products'], f)
    with open(terms_file, 'w') as f:
        json.dump(full_data['terms']['OnDemand'], f)
    logger.debug('Split complete')


def get_sku(location, instance_type, products_file):
    """
    Optimized JSON parsing to find the SKU for the provided location and type.
    """
    # SKU dicts have prefixes like 76V3SF2FJC3ZR3GH
    sku_dict_prefix = re.compile('^[a-zA-Z0-9]+$')
    sku = ''
    matches = 0
    event_count = 0
    with open(products_file) as f:
        parser = ijson.parse(f)
        for prefix, event, value in parser:
            event_count += 1
            if prefix.endswith('.sku'):
                # Save the SKU of the current SKU dict
                sku = value
            elif prefix.endswith('.productFamily') and value == "Compute Instance":
                matches += 1
            elif prefix.endswith('.location') and value == location:
                matches += 1
            elif prefix.endswith('.instanceType') and value == instance_type:
                matches += 1
            elif event == 'end_map' and sku_dict_prefix.match(prefix):
                # We've reached the end of the SKU dict, is this the right one?
                if matches == 3:
                    # All three values matched, this is our sku
                    logger.debug("SKU: {}".format(sku))
                    return sku
                else:
                    # This wasn't the right SKU dict, reset our matches
                    matches = 0


def get_price(sku, terms_file):
    event_count = 0
    with open(terms_file) as file:
        parser = ijson.parse(file)
        for prefix, event, value in parser:
            event_count += 1
            if prefix.endswith('.pricePerUnit.USD') and sku in prefix:
                logger.debug('Hourly price: {}'.format(value))
                return value


def compute_rate(group, environment, resource_technology, cfvs, pcvss,
                 os_build, apps, quantity=1, **kwargs):
    # Download AWS pricing data, if it doesn't already exist.
    file_location = "{}/full_pricing_data.json".format(RATE_HOOK_DIR)
    download_file(AWS_URL, file_location)

    # Split file into two parts: one to look up the SKU for this instance type,
    # and one to look up the price for a SKU. The smaller file sizes speed up
    # calculation by several seconds.
    products_file = "{}/products_data.json".format(RATE_HOOK_DIR)
    terms_file = "{}/terms_data.json".format(RATE_HOOK_DIR)
    split_file(file_location, products_file, terms_file)

    server = kwargs.get('server', None)
    # If being called from a context where we have a server object that stores
    # AWS-specific info, reference that first for the instance type
    instance_type = None
    region_name = None

    if server and hasattr(server, 'ec2serverinfo') and server.ec2serverinfo:
        instance_type = server.ec2serverinfo.instance_type
        region_name = server.ec2serverinfo.ec2_region

    if not instance_type:
        for cfv in cfvs:
            if cfv.field.name == 'instance_type' and cfv.value:
                instance_type = cfv.value
                break

    if not instance_type:
        # Perhaps the instance_type is in a preconfiguration.
        for pcvs in pcvss:
            instance_type_cfvs = pcvs.custom_field_values.filter(field__name='instance_type')
            if instance_type_cfvs.count() > 0:
                # Let's just take the first instance_type returned if we get more than 1.
                instance_type = instance_type_cfvs[0].value
                break

    if not instance_type:
        logger.warning("Could not determine instance type, unable to calculate rate")
        return {}

    if not region_name:
        rh = AWSHandler.objects.first()
        region_name = rh.get_env_region(environment)

    if not region_name:
        logger.warning("Could not determine region, unable to calculate rate.")
        return {}

    # Locations are full titles, like "US West (N. California)"
    location = get_region_title(region_name)

    cache_key = "{}:{}".format(region_name, instance_type)
    rate = cache.get(cache_key)

    if rate:
        logger.debug("Using cached rate {} for {} type in {}"
                     .format(rate, instance_type, location))
    else:
        sku = get_sku(location, instance_type, products_file)
        if sku is None:
            logger.warning('No Product SKU was found in the AWS pricing file '
                           'for region {} and instance type {}.'
                           .format(location, instance_type))
            return {}
        rate = get_price(sku, terms_file)
        cache.set(cache_key, rate)

    rate_time_unit = GlobalPreferences.objects.get().rate_time_unit
    number_of_hours = NUMBER_OF_HOURS.get(rate_time_unit, 0)
    rate_dict = {
    'Hardware': {
        "Instance Type": Decimal(rate) * number_of_hours * quantity
      },
    }
    default_rate = default_compute_rate(group=group,environment=environment,resource_technology=resource_technology,cfvs=cfvs,pcvss=pcvss,os_build=os_build,apps=apps,quantity=quantity,**kwargs)
    rate_dict['Software'] = default_rate.get('Software', 0)
    rate_dict['Extra'] = default_rate.get('Extra', 0)
    return rate_dict