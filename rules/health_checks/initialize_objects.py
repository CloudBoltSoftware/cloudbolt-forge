
all_cfs = [
    {
        'name': 'health_check_config',
        'label': 'Health Check Config',
        'type': 'CODE',
        'show_on_servers': True,
        'description': ('JSON data specifying urls to perform health checks on.')
    }
]

hooks = [
    {
        'name': 'Perform Resource Health Checks',
        'description': 'Used by auto-scaling conditional rule',
        'shared': False,
        'enabled': True,
        'hook_point': None,
        'module': 'resource_health_checks.py',
    }
]

