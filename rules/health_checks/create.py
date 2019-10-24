from c2_wrapper import create_custom_field, create_rule, create_hook
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
        'module': 'health_alerts.py',
}

rule = {
        'name': 'resource_health_checks',
        'label': 'Perform Resource Health Checks',
        'description': 'Resource Health Check support',
        'condition': {
            'name': 'Perform Resource Health Checks',
            'description': 'Resource Health Check support',
            'shared': False,
            'module': 'resource_health_checks.py',
        },
        'action': alerting_action_dict
}


def run(job, *args, **kwargs):
    set_progress("Creating health_check_config Custom Field...")
    create_custom_field(**health_check_cf)

    set_progress("Creating Resource Health Checks Rule...")
    create_rule(**rule)

    set_progress("Done creating objects for resource health checks.")

    return "", "", ""
