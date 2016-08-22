#!/usr/bin/env python

"""
A hook that will update (creating when needed) group membership and permissions
based on the user's ldap settings.

OUs will become CloudBolt groups, membership on special ldap groups:
CB-Requestors, CB-Approvers, CB-GroupManagers and CB-ResourceManagers will
dictate the permissions users will get on the cloudbolt group that matches the
user's current OU.
"""

import sys

from accounts.models import Group, GroupType, UserProfile


def run(job, logger=None, **kwargs):
    debug("Running hook {}".format(__name__), logger)

    users = kwargs.get('users', None)
    for user_profile in users:
        debug("Fetching external data for user: {}".format(user_profile), logger)
        skip_user = False
        data = user_profile.ldap.runUserSearch(user_profile.user.username, find="")
        if not data:
            return ("FAILURE", "", "")

        # create cloudbolt groups as needed
        dn = data[0][0]
        ou_group_type, _ = GroupType.objects.get_or_create(group_type="Organizational Unit")
        parent_group = None
        for element in dn.split(",")[::-1]:
            if element.startswith("OU="):
                group_name = element[3:]
                group = Group.objects.filter(name=group_name)
                if not group:
                    debug("Creating group {} as part of external user sync".format(group_name),
                          logger)
                    group = Group.objects.create(
                        name=group_name, type=ou_group_type, parent=parent_group
                    )
                else:
                    group = group[0]
                    if group.parent != parent_group:
                        #this is a duplicate OU in LDAP/AD, skip permission setting
                        skip_user = True
                        break
                parent_group = group

        if skip_user:
            continue

        # set users permissions based on special group membership in LDAP/AD
        # for each permission first remove the group if there

        user_profile.requestors.remove(group)
        user_profile.approvers.remove(group)
        user_profile.user_admins.remove(group)
        user_profile.resource_admins.remove(group)

        # add Viewer permission
        user_profile.viewers.add(group)

        # Add additional permissions based on LDAP/AD group membership
        if 'memberOf' in data[0][1]:
            ldap_groups = data[0][1]['memberOf']

            for lgroup in ldap_groups:
                if "CB-Requestors" in lgroup:
                    # Requestor
                    user_profile.requestors.add(group)
                if "CB-Approvers" in lgroup:
                    # Approver
                    user_profile.approvers.add(group)
                if "CB-GroupManagers" in lgroup:
                    # Group Admin
                    user_profile.user_admins.add(group)
                if "CB-ResourceManagers" in lgroup:
                    # Resource Admin
                    user_profile.resource_admins.add(group)

    return "", "", ""


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
    status, msg, err = run(None, None, users=[profile])
    print "status, msg, err = ", (status, msg, err)
