#!/usr/bin/env python

"""
An example hook that will update (creating when needed) group membership and permissions
based on the user's ldap settings.

This will create 3 groups in CB: Silver, Bronze, and Gold, and place users in those groups based
on whether they are in corresponding security groups in AD.

The security group names are specified in CB action inputs so that the names of these security
groups can be set/changed from the CB UI without modifying this Python code.

If the user belongs to the security group set in the action input for viewers_security_group_name,
approvers_security_group_name, resource_admins_security_group_name,
or group_admins_security_group_name they will be added to  the corresponding role on all three
"metal" groups in CB (Silver, Bronze, and Gold).

If the user belongs to requesters_security_group_name-<metal name> (ex. "Requesters-Gold"),
they will be added as a requester in the Gold group.

If the user belongs to cb_admins_security_group_name, they will be granted CB admin and super
admin permissions.

Any permissions that the user should not have, based on their security group membership in AD,
will be removed.
"""

import sys

from accounts.models import Group, GroupType, UserProfile
from common.methods import set_progress

GROUP_LEVELS = ["Silver", "Bronze", "Gold"]


def run(job, logger=None, **kwargs):
    debug("Running hook {}".format(__name__), logger)

    users = kwargs.get('users', None)
    for user_profile in users:
        debug("Fetching external data for user: {}".format(user_profile), logger)
        data = user_profile.ldap.runUserSearch(user_profile.user.username, find="")
        # debug("{}".format(data), logger)
        if not data:
            return "FAILURE", "", ""

        groups = get_or_create_groups()
        set_user_permissions(user_profile, groups, data)
    return "", "", ""


def get_or_create_groups():
    """
    Get or create CloudBolt groups as needed, for each group defined in GROUP_LEVELS.

    :return: a dict where the keys are the names of the groups and the values are the group objects
    """
    groups = {}
    group_type, _ = GroupType.objects.get_or_create(group_type="Organization")
    for level in GROUP_LEVELS:
        group, _ = Group.objects.get_or_create(
            name=level, type=group_type, parent=None
        )
        groups[level] = group
    return groups


def add_user_to_groups(user_profile, groups, role):
    """
    Adds a user to a list of groups, in the specified role.

    :param user_profile: a CB UserProfile object
    :param groups: a list of Group objects
    :param role: a string that should be "viewers", "requesters", "approvers",
    "resource_admins", or "user_admins"
    :return: None
    """
    set_progress("Adding {} to {} role on these groups: {}".format(user_profile, role, groups))
    role_relationship = getattr(user_profile, role)
    role_relationship.add(*groups)


def set_user_permissions(user_profile, groups, data):
    """
    Set users permissions on the 3 groups based on security group membership in LDAP/AD

    Also make them a CB admin, super admin, and env admin if they are a member of the
    corresponding security group in AD.
    """
    group_objects = groups.values()
    is_admin = False  # keeps track of whether they have been found to be in the CB admin sec group

    # First remove all permissions from the groups we are managing
    user_profile.requestors.remove(*group_objects)
    user_profile.approvers.remove(*group_objects)
    user_profile.user_admins.remove(*group_objects)
    user_profile.resource_admins.remove(*group_objects)

    user = user_profile.user

    # Add additional permissions based on LDAP/AD group membership
    if 'memberOf' not in data[0][1]:
        set_progress("No memberOf information found for user {}, skipping adding user to any "
                     "roles".format(user_profile))
        return

    ldap_groups = data[0][1]['memberOf']
    set_progress("{} was found to be a member of these security groups: {}".format(
        user_profile, ldap_groups))

    # for each security group the user is in
    for lgroup in ldap_groups:
        # if the viewer security group name is anywhere in the name of the security group
        if "{{viewers_security_group_name}}" in lgroup:
            # Add user as an viewer in all 3 groups in CB
            add_user_to_groups(user_profile, group_objects, "viewers")
        if "{{requesters_security_group_name}}" in lgroup:
            # Requesters are different - check to see if sec group name ends in any one of the
            # group level names ('silver', 'bronze', or 'gold'). If so, add to the corresponding
            # group in CB as a requester.
            for group_level in GROUP_LEVELS:
                if group_level in lgroup:
                    group = groups[group_level]
                    set_progress("Adding {} to {} as a requester".format(user_profile, group))
                    user_profile.requestors.add(group)
        if "{{approvers_security_group_name}}" in lgroup:
            # Add user as an approver in all 3 groups in CB
            add_user_to_groups(user_profile, group_objects, "approvers")
        if "{{group_admins_security_group_name}}" in lgroup:
            # Add user as a user_admin (group admin) in all 3 groups in CB
            add_user_to_groups(user_profile, group_objects, "user_admins")
        if "{{resource_admins_security_group_name}}" in lgroup:
            # Add user as a resource_admin in all 3 groups in CB
            add_user_to_groups(user_profile, group_objects, "resource_admins")

        # process CB admin perms
        if "{{cb_admins_security_group_name}}" in lgroup:
            set_progress("Making the user an admin")
            # Make the user a super admin, CB admin, and env admin
            user_profile.super_admin = True
            user_profile.environment_admin = True
            user_profile.save()
            # set the django user permission that maps to cb_admin
            user.is_superuser = True
            user.save()
            is_admin = True

    if not is_admin:
        # after checking all groups, the user was not part of any that make them a CB admin
        set_progress("Removing admin permissions from the user")
        # Make the user not a super admiin, CB admin, and env admin
        user_profile.super_admin = False
        user_profile.environment_admin = False
        user_profile.save()
        # unset the django user permission that maps to cb_admin
        user.is_superuser = False
        user.save()


def debug(message, logger):
    if logger:
        logger.debug(message)
    else:
        print message

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("usage: %s <CloudBolt UserProfile.username>\n" % (sys.argv[0]))
        sys.exit(2)
    username = sys.argv[1]
    try:
        profile = UserProfile.objects.get(user__username=username)
    except:
        print "Failed to fetch user with username: ", username
        exit(1)
    # Uncomment this to test calling into AD and sync users
    # status, msg, err = run(None, None, users=[profile])
    # print "status, msg, err = ", (status, msg, err)

    # Test just the setting of group membership & roles in CB based on fake, hardcoded data,
    # bypassing AD
    data = [[0, {"memberOf": [
        "{{cb_admins_security_group_name}}",
        "{{requesters_security_group_name}}-Gold", "{{approvers_security_group_name}}",
    ]}]]
    groups = get_or_create_groups()
    set_user_permissions(profile, groups, data)
