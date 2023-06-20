from django.shortcuts import render

from extensions.views import dashboard_extension
from utilities.get_current_userprofile import get_current_userprofile


GROUPS_LIMIT = 10

@dashboard_extension(title="Group Quotas",
                     description="Displays a list of group quotas.")
def group_quotas_dashboard(request):
    """
    Display a list of group quotas in a CloudBolt dashboard widget.
    :param request: HTTP request
    """
    up = get_current_userprofile()
    groups = [group for group in up.get_groups()]
    group_quotas = []
    group_num = 1
    for group in groups:
        quota_set = group.quota_set
        try:
            cpu_cnt = f'{int(quota_set.cpu_cnt.used)} / ' \
                      f'{int(quota_set.cpu_cnt.limit)}'
        except OverflowError:
            cpu_cnt = f'{int(quota_set.cpu_cnt.used)} / NA'
        try:
            mem_size = f'{int(quota_set.mem_size.used)} / ' \
                       f'{int(quota_set.mem_size.limit)}'
        except OverflowError:
            mem_size = f'{int(quota_set.mem_size.used)} / NA'
        try:
            rate = f'${int(quota_set.rate.used)} / ${int(quota_set.rate.limit)}'
        except OverflowError:
            rate = f'${int(quota_set.rate.used)} / NA'
        try:
            vm_cnt = f'{int(quota_set.vm_cnt.used)} / ' \
                     f'{int(quota_set.vm_cnt.limit)}'
        except OverflowError:
            vm_cnt = f'{int(quota_set.vm_cnt.used)} / NA'
        try:
            disk_size = f'{int(quota_set.disk_size.used)} / ' \
                        f'{int(quota_set.disk_size.limit)}'
        except OverflowError:
            disk_size = f'{int(quota_set.disk_size.used)} / NA'

        group_quotas.append({
            "name": group.name,
            "id": group.id,
            "cpu_cnt": cpu_cnt,
            "mem_size": mem_size,
            "rate": rate,
            "vm_cnt": vm_cnt,
            "disk_size": disk_size,
        })
        group_num += 1
        if group_num > GROUPS_LIMIT:
            break

    context = {"userprofile": up, "group_quotas": group_quotas}

    return render(
        request, template_name="group_quotas/templates/widget.html",
        context=context
    )
