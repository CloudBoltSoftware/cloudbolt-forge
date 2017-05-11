import sys
from accounts.models import Group, GroupType, UserProfile


def run(job, logger=None, **kwargs):
    logger.debug("Running hook {}".format(__name__), logger)
    users = kwargs.get('users', None)
    for user_profile in users:
        # Set the default group below by name or ID.
        g = Group.objects.filter(name="Default Group").first()
        logger.debug("Got user %s", user_profile.id)
        logger.debug("Group: %s", g.name)

        # Pre-7.2 version
        if g.is_resource_admin(user_profile):
            # Bypass setting permissions if the user is a Resource Admin in group.
            logger.debug("User is group admin")
        else:
            user_profile.requestors.add(g)
            user_profile.approvers.add(g)
            user_profile.viewers.remove(g)

        # 7.2+ version
        # from accounts.models import Role, GroupRoleMembership
        # if GroupRoleMembership.objects.filter(
        #         profile=user_profile, role__name='resource_admin',
        #         group=g).exists():
        #     # Bypass setting permissions if the user is a Resource Admin in group.
        #     logger.debug("User is group admin")
        # else:
        #     roles = ["requestor", "approver", "viewer"]
        #     for role_name in roles:
        #         role = Role.objects.get(name=role_name)
        #         user_profile.add_role_for_group(role, g)

        logger.debug("Completed.")
    return "", "", ""
