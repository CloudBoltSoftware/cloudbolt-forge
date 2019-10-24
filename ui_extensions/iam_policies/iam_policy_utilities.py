import os

from cbhooks.hookmodules.content_library.cache_content import write_list_to_file

IAM_POLICY_CACHE_LOCATION_PATH = '/var/opt/cloudbolt/iam_policies/'


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
        'description': ('Fetches and stores the IAM Policies for all configured AWS Resource Handlers. These '
                        'policy lists are stored in /var/opt/cloudbolt/iam_policies/.'),
        'schedule': '0 23 * * *',
        'enabled': True,
    }
    create_recurring_job(get_iam_policies_recurring_job)


def get_iam_policies(handler):
    """
    Instantiate the IAM client and request a full list of Policies.

    We then write this list to the filesystem so that the corresponding XUI for this feature
    can read previously discovered objects without having to call this API each time the
    AWS RH detail page is viewed.
    """
    wrapper = handler.get_api_wrapper()
    iam_client = wrapper.get_boto3_client('iam', handler.serviceaccount, handler.servicepasswd, None)

    response = iam_client.list_policies(MaxItems=1000)

    iam_policies = []
    for policy in response['Policies']:
        iam_policies.append(
            {
                "arn": policy['Arn'],
                "path": policy['Path'],
                "name": policy['PolicyName'],
            }
        )

    os.makedirs(IAM_POLICY_CACHE_LOCATION_PATH, exist_ok=True)
    path = os.path.join(IAM_POLICY_CACHE_LOCATION_PATH, 'handler-{}-policies.json'.format(handler.id))
    write_list_to_file(iam_policies, path)

    return iam_policies


def determine_most_recent_iam_policy(version_ids):
    """
    These version ids are provided by AWS and are in the format ['v6', 'v4', 'v1'].
    """
    if len(version_ids) == 1:
        return version_ids[0]
    integer_versions = [int(v[1:]) for v in version_ids]
    biggest_int = sorted(integer_versions, reverse=True)[0]
    return 'v{}'.format(biggest_int)


def get_iam_policy_details(handler, policy_arn):
    """
    To be able to display the actual document for a policy, we need to tell AWS which version of the policy
    we want to see. So we first list all the versions of the document, then ask for the most recent version.
    """
    wrapper = handler.get_api_wrapper()
    iam_client = wrapper.get_boto3_client('iam', handler.serviceaccount, handler.servicepasswd, None)

    policy_versions = iam_client.list_policy_versions(PolicyArn=policy_arn)
    version_ids = [v['VersionId'] for v in policy_versions['Versions']]
    most_recent_version = determine_most_recent_iam_policy(version_ids)

    policy_details = iam_client.get_policy_version(PolicyArn=policy_arn, VersionId=most_recent_version)
    return policy_details
