from accounts.models import Group


def get_cmp_group_map():
    return {g.name: g for g in Group.objects.all()}


def get_unmatched_cmp_groups(cmp_group_map, azure_groups):
    azure_names = [g.get("displayName") for g in azure_groups]
    return [
        g for name, g in cmp_group_map.items()
        if name not in azure_names
    ]