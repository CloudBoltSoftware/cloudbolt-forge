from common.methods import set_progress
from infrastructure.models import Environment
from django.db.models import Q


def generate_options_for_environment(field, rt_name=None, **kwargs):
    """
    Generate a list of environments to choose from. Returns a list of id, name tuples
    """
    set_progress(f'kwargs: {kwargs}')
    group = kwargs.get("group")
    set_progress("Group: {}".format(group))
    if not group:
        return None
    if rt_name:
        envs = Environment.objects.filter(
            (Q(group__in=[group]) | Q(group=None)) &
            Q(resource_handler__resource_technology__name=rt_name)
        )
    else:
        envs = Environment.objects.filter(
            Q(group__in=[group]) | Q(group=None)
        )
    envs = [(env.id, env.name) for env in envs if env.is_unassigned == False]
    if not envs:
        envs = [("", "------No environments available------")]
    return envs
