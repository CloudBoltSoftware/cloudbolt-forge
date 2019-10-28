"""
Python script for creating all necessary objects for the Resource Health Checks rule.

Instructions:
Copy the entire 'health_checks' directory into /var/opt/cloudbolt/proserv
Run this from the commandline;
    `python /var/opt/cloudbolt/proserv/health_checks/create.py`

Go to Admin/Rules and see your rule.
Read the README.md for more instructions on using the rule.
"""

import os
import sys

# Set the path to where settings can be found.
from mock import patch

sys.path.insert(0, '/opt/cloudbolt/')

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

if __name__ == "__main__":
    import django
    django.setup()

# Now set the path to point to the proserv dir where this should run from
cloudbolt_rootdir = '/var/opt/cloudbolt/proserv'
sys.path.insert(0, cloudbolt_rootdir)

from c2_wrapper import create_custom_field, create_rule, create_hook
from cbhooks.models import CloudBoltHook
from common.methods import set_progress

health_check_cf = {
        'name': 'health_check_config',
        'label': 'Health Check Config',
        'type': 'CODE',
        'show_on_servers': True,
        'description': ('JSON data specifying what to perform health checks on.')
    }

alerting_action_dict = {
        'name': 'Alert Channels for Health Checks',
        'shared': False,
        'enabled': True,
        'hook_point': None,
        'module': 'health_checks/health_alerts.py'
}

rule = {
        'name': 'resource_health_checks',
        'label': 'Perform Resource Health Checks',
        'description': 'Resource Health Check support',
        'condition': {
            'name': 'Perform Resource Health Checks',
            'description': 'Resource Health Check support',
            'shared': False,
            'module': 'health_checks/resource_health_checks.py'
        },
        'action': alerting_action_dict
}


def run():
    set_progress("Creating health_check_config Custom Field...")
    create_custom_field(**health_check_cf)

    set_progress("Creating Resource Health Checks Rule...")
    with patch('c2_wrapper.cloudbolt_rootdir', cloudbolt_rootdir):
        create_rule(**rule)

    set_progress("Done creating objects for resource health checks.")
    return


if __name__ == '__main__':
    print(run())
    sys.exit(0)
