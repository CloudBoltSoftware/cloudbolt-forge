#!/usr/local/bin/python

# Bernard Sanders 1/26/2012
# should be run from CloudBolt 'src' directory
# ex. usage: ./grant_all_perms.py -u bernard

import sys
import os

if __name__ == "__main__":
    import django

    django.setup()


os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
sys.path.append("..")

from django.contrib.auth.models import User

from accounts.models import Group, Role, GroupRoleMembership


def grant_all_perms(user):
    user = User.objects.filter(username=user)[0]
    profile = user.userprofile
    groups = Group.objects.all()

    memberships = []
    for group in groups:
        for role in Role.assignable_objects.all():
            memberships.append(
                GroupRoleMembership(role=role, profile=profile, group=group)
            )

    GroupRoleMembership.objects.bulk_create(memberships)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gives user all roles on all groups")
    parser.add_argument("-u", help="user", required=1)
    args = parser.parse_args()
    grant_all_perms(args.u)
