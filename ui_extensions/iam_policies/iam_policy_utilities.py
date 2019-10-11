def setup_aws_iam_policies():
    from c2_wrapper import create_hook
    from initialize.create_objects import create_recurring_job

    get_iam_policies_action = {
        'label': 'AWS IAM Policy Caching',
        'name': 'aws_iam_policy_caching',
        'description': ("Fetches and stores all IAM Policies associated with "
                        "a given AWS Resource Handler."),
        'hook_point': None,
        'module': '/var/opt/cloudbolt/proserv/xui/iam_policies/aws_iam_policy_caching.py',
        'enabled': True,
    }
    create_hook(**get_iam_policies_action)

    get_iam_policies_recurring_job = {
        'name': 'AWS IAM Policy Caching',
        'type': 'recurring_action',
        'hook_name': 'AWS IAM Policy Caching',
    }
    create_recurring_job(get_iam_policies_recurring_job)
