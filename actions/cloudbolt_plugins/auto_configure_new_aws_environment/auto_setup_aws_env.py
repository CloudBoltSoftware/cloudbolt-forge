"""
A post-environment creation CB plug-in that sets up several aspects of new AWS environments to obviate the need to
do that manually. This does not doing anything when a new environment is created from the environment list page,
but it does when a new environment is created from the details page of an AWS resource handler (on the Regions tab).
It sets up the following:

 * AMIs
 * A single keypair option (with the same name as the group)
 * The group association
 * The instances sizes (from an Environment named "Template" for this RH)

Assumptions:

 * The resource handler name ends with the group name, which causes the default environment names to have the group
   name right before the first ')' character
 * The key pair for this group has the same name as the group, but all lowercase
 * There is an environment called "Template" within this resource handler. The instance type options will be copied from
   this environment.

This is just an example and these assumptions won't always be true. You can use this plug-in as a starting point and
modify the logic to suit your needs.

For more information, read the run() method.
"""

import re
from typing import Optional, Tuple

from accounts.models import Group
from common.methods import set_progress
from infrastructure.models import Environment

from resourcehandlers.aws.models import AWSHandler, AmazonMachineImage
from resourcehandlers.aws.services import import_selected_amis

group_name_from_env_name_re = re.compile(" ([A-Za-z]+)\)")


def run(job, *args, **kwargs):
    env = kwargs.get('environment')
    handler, region = extract_and_check_parameters(env)
    if not handler:
        return

    import_amis(handler, region, env)
    group = get_group_from_env_name(env.name)
    if group:
        add_keypair_with_name(env, group.name)
        group.environments.add(env)

    template_env = Environment.objects.filter(name="Template", resource_handler=handler)
    if template_env.exists():
        template_env = template_env.first()
        copy_instance_sizes_from_env(template_env, env)


def get_group_from_env_name(env_name: str) -> Optional[Group]:
    """
    Pull the group name out of the env name, and try to find a group object in CB for that

    Example env name: (AWS ACME) us-east-1 cloudbolt-acme-vpc
    The group name in this case is ACME
    """
    mo = group_name_from_env_name_re.search(env_name)
    if not mo:
        set_progress(f"Could not find a group name in environment name {env_name}")
        return None
    group_name = mo.groups()[0]
    groups = Group.objects.filter(name=group_name)
    if not groups.exists():
        set_progress(f"Could not find a group with name {group_name}")
        return None
    return groups.first()


def copy_instance_sizes_from_env(src_env: Environment, dst_env: Environment) -> None:
    instance_types = src_env.custom_field_options.filter(field__name="instance_type")
    set_progress(f"Setting {len(instance_types)} instance types from {src_env} on {dst_env}")
    dst_env.replace_cf_options("instance_type", instance_types)


def add_keypair_with_name(env: Environment, name: str) -> None:
    set_progress(f"Setting key option {name} on {env}")
    env.replace_cf_options("key_name", [name.lower()])


def extract_and_check_parameters(env: Environment) -> Tuple[Optional[AWSHandler], Optional[str]]:
    """
    Extract and return handler and region from the environment.

    If anything is wrong, and this plug-in should be skipped, print a message indicating why and return (None, None)
    """

    if env.os_builds.exists():
        # Not a perfect way to check if this is running at env creation time, but close enough.
        set_progress("This environment has OSBs, so it is probably not new, skipping automatic AWS "
                     "environment setup")
        return None, None

    handler = env.resource_handler
    if not handler:
        set_progress("No resource handler for this environment, skipping automatic AWS environment setup")
        return None, None

    handler = handler.cast()
    if not isinstance(handler, AWSHandler):
        set_progress("This environment's handler is not AWS, skipping automatic AWS environment setup")
        return None, None

    region = handler.get_env_region(env)
    if not region:
        set_progress(
            "This environment's region is not set, skipping automatic AWS environment setup. If you want automatic "
            "environment setup, create the environment from the Regions tab on the AWS Resource Handler's details "
            "page.")
        return None, None
    return handler, region


def import_amis(handler: AWSHandler, region: str, env: Environment) -> None:
    """
    Fine all AMIs on `handler` and add the OSB for each corresponding AMIs for `region` to `env`.
    """
    # Get all AMIs on this RH with a distinct AMI name and add them to this new environment
    ami_names = handler.os_build_attributes.all().values_list("template_name", flat=True).distinct()
    dicts_for_import = handler.get_ami_dicts_for_region_by_names(ami_names, region)
    ami_ids_to_import = [dict_for_import["ami_id"] for dict_for_import in dicts_for_import]

    ami_ids_to_create = []
    for ami_id in ami_ids_to_import:
        ami = AmazonMachineImage.objects.filter(resourcehandler=handler, ami_id=ami_id)
        if ami.exists():
            # The AMI already exists for this RH, the region must already have been imported for a different
            # environment. Reuse this AMI object and add its OSB to this new environment.
            ami = ami.first()
            env.os_builds.add(ami.os_build)
        else:
            # The AMI does not yet exist in the DB for this RH. Store it for later to import from scratch.
            ami_ids_to_create.append(ami_id)
    import_selected_amis(ami_ids_to_create, dicts_for_import, handler, region, [env])
