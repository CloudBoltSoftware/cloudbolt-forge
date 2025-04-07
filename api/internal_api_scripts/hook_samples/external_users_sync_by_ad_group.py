#!/usr/bin/env python

"""
WARNING: This script uses old-style roles and is incompatible with CB 7.2.

A hook that will update (creating when needed) group membership and permissions
based on the user's ldap group settings.

For any group that follows the format { business_unit }_{ permission } where
permission in ['requestors', 'approvers', 'admins'] this script will create (if
needed) a CloudBolt group that represents the { business_unit } and give the
user the appropriate permission.
"""

import sys
import threading
import logging

if __name__ == '__main__':
    import django
    django.setup()

from accounts.models import Group, GroupType, UserProfile


def run(job, logger=None, **kwargs):
    debug("Running hook {}".format(__name__), logger)

    group_type, _ = GroupType.objects.get_or_create(group_type="Organization")

    users = kwargs.get('users', None)
    for user_profile in users:
        debug("Fetching external data for user: {}".format(user_profile), logger)
        data = user_profile.ldap.runUserSearch(user_profile.user.username, find="")
        #debug("{}".format(data), logger)
        if not data:
            return ("FAILURE", "", "")

        # set users permissions based on special group membership in LDAP/AD
        if 'memberOf' in data[0][1]:
            ldap_groups = data[0][1]['memberOf']

            for lgroup in ldap_groups:

                #fetch the group's CN
                cn = lgroup.split(",")[0].replace("CN=", "")

                if "IAAS_superadmins" in cn:
                    user_profile.super_admin = True
                    user_profile.environment_admin = True
                    user_profile.save()
                    # set the django user permission that maps to cb_admin
                    user = user_profile.user
                    user.is_superuser = True
                    user.save()

                if ((cn.endswith("_requestors") or cn.endswith("_approvers") or
                        cn.endswith("_admins")) and cn.startswith("IAAS")):
                    iaas, group_name, permission = cn.split("_")
                    group, _ = Group.objects.get_or_create(name=group_name, type=group_type)

                    # add Viewer permission
                    user_profile.viewers.add(group)

                    if "requestors" in permission:
                        # Requestor
                        user_profile.requestors.add(group)
                    elif "managers" in permission:
                        # Approver
                        user_profile.approvers.add(group)
                    elif "admins" in permission:
                        # Group Admin
                        user_profile.user_admins.add(group)


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
    threading.current_thread().logger = logging.getLogger()
    username = sys.argv[1]
    try:
        profile = UserProfile.objects.get(user__username=username)
    except:
        print "Failed to fetch user with username: ", username
        exit(1)
    status, msg, err = run(None, None, users=[profile])
    print "status, msg, err = ", (status, msg, err)
