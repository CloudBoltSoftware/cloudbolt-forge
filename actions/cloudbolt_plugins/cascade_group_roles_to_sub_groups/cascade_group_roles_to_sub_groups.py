# Post Group Creation Orch. Action

from accounts.models import Role, GroupRoleMembership

def run(group, *args, **kwargs):
    parent = group.parent
    
    if parent:
        roles = parent.grouprolemembership_set.all()
        for role in roles:
            GroupRoleMembership.objects.get_or_create(
                profile=role.profile, role=role.role, group=group)
    
    return "SUCCESS","",""
