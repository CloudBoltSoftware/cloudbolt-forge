#!/bin/env python
"""
An example CloudBolt post-group-creation hook script that adds the user permissions
from its parent group.
"""
from common.methods import set_progress


def run(job, group, logger=None):
    roles_to_sync = ['user_admins',
                     'resource_admins',
                     'approvers',
                     'requestors',
                     'viewers']

    if group.parent is None:
        set_progress("No parent group found to sync users from.", job)
        return "", "", ""

    set_progress("Syncing users from parent group {}".format(group.parent), job)

    for role in roles_to_sync:
        group_role_members = getattr(group, role)
        parent_role_members = getattr(group.parent, role)
        for user in parent_role_members.all():
            group_role_members.add(user)

    return "", "", ""
