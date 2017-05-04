from accounts.models import UserProfile, Group

__author__ = 'rick@cloudbolt.io'

import sys
import logging
import threading

"""
This hook allows cloudbolt admins to automatically map users in named LDAP
groups to CB groups upon login. The mapping below determine which LDAP group is
mapped to which CB group as well as any user roles that should be applied to the
user. By default, if no role is specified, the user is mapped to the VIEWER role
for the LDAP group.

If the CloudBolt group does NOT exist, it will be automatically created under
the CloudBolt specified by ROOT_GROUP_NAME. If this behavior is not desired, set
ROOT_GROUP_NAME to null.
"""

ROLE_REQUESTOR = 'requestor'
ROLE_VIEWER = 'viewer'
ROLE_GROUP_ADMIN = 'group_admin'
ROLE_RESOURCE_ADMIN = 'resource_admin'
ROLE_APPROVER = 'approver'

ROOT_GROUP_NAME = 'CloudBolt'

GROUP_MAPPINGS = {
    'LDAP DN': {
        'cb_group': 'CloudBolt Group Name',
        'roles': [
            ROLE_APPROVER,
            ROLE_REQUESTOR,
            ROLE_RESOURCE_ADMIN,
            ROLE_GROUP_ADMIN,
        ]
    },
}


def run(job, logger=None, **kwargs):
    debug("Running hook {}".format(__name__), logger)

    try:
        root_group = Group.objects.get(name=ROOT_GROUP_NAME)
    except:
        root_group = None

    users = kwargs.get('users', None)
    for user_profile in users:
        debug("Fetching LDAP info for user: {}".format(user_profile), logger)
        data = user_profile.ldap.runUserSearch(user_profile.user.username, find="")

        if not data:
            return "FAILURE", "", ""

        ldap_groups = []
        if 'memberOf' in data[0][1]:
            ldap_groups = data[0][1]['memberOf']

        for ldap_group in ldap_groups:
            if is_mapped_to_cloudbolt(ldap_group):
                mapping = GROUP_MAPPINGS[ldap_group]

                if ROOT_GROUP_NAME:
                    cb_group, _ = Group.objects.get_or_create(
                        name=mapping['cb_group'], type=root_group.type, parent=root_group)
                else:
                    try:
                        cb_group, _ = Group.objects.get(name=mapping['cb_group'])
                    except:
                        return "FAILURE", "", ""

                # by default add user to viewer role
                user_profile.viewers.add(cb_group)

                # reset user roles
                user_profile.requestors.remove(cb_group)
                user_profile.approvers.remove(cb_group)
                user_profile.resource_admins.remove(cb_group)
                user_profile.user_admins.remove(cb_group)

                if mapping['roles']:
                    for role in mapping['roles']:
                        if role == ROLE_REQUESTOR:
                            user_profile.requestors.add(cb_group)

                        if role == ROLE_APPROVER:
                            user_profile.approvers.add(cb_group)

                        if role == ROLE_RESOURCE_ADMIN:
                            user_profile.resource_admins.add(cb_group)

                        if role == ROLE_GROUP_ADMIN:
                            user_profile.user_admins.add(cb_group)

    return 'SUCCESS', '', ''


def is_mapped_to_cloudbolt(group_common_name):
    for mapping in GROUP_MAPPINGS:
        if mapping.lower() == group_common_name.lower():
            return True
    return False


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
