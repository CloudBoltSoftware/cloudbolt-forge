from django.shortcuts import render

from costs.models import render_rate
from costs.utils import get_resource_rate, get_rate_hook
from extensions.views import tab_extension, TabExtensionDelegate
from infrastructure.models import Server
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


class ServerCostDetailsTabDelegate(TabExtensionDelegate):
    def should_display(self):
        return True


@tab_extension(model=Server, title='Costs',
               delegate=ServerCostDetailsTabDelegate)
def cost_details_tab(request, obj_id):
    server = Server.objects.get(id=obj_id)

    env = server.environment

    cost = {
        'summary': {
            'hw_rate_display': render_rate(server.hw_rate),
            'sw_rate_display': render_rate(server.sw_rate),
            'extra_rate_display': render_rate(server.extra_rate),
            'total_rate_display': render_rate(server.total_rate)
        },
        'detail': {
            'cpu': {
                'unit_cost': _get_cost('cpu_cnt', env),
                'qty': server.cpu_cnt,
                'ext_cost': 0,
                'ext_cost_display': '-'
            },
            'mem': {
                'unit_cost': _get_cost('mem_size', env),
                'qty': server.mem_size,
                'ext_cost': 0,
                'ext_cost_display': '-'
            },
            'disk': {
                'unit_cost': _get_cost('disk_size', env),
                'qty': 0,
                'ext_cost': 0,
                'ext_cost_display': '-'
            },
        },
        'disks': [],
        'params': [],
        'apps': [],
        'os_build': {}
    }

    logger.info(cost)

    _update_detail_costs(cost, server)
    _update_disks(cost, server)
    _update_osbuild_rate(cost, server)
    _update_app_rates(cost, server)
    _update_param_rates(cost, server)
    _calc_totals(cost)

    return render(request, 'server_cost_details/templates/cost_details.html',
                  dict(
                      server=server, costs=cost
                  ))


def _get_cost(cf_name, env):
    cost = get_resource_rate(cf_name, env)
    if not cost:
        cost = get_resource_rate(cf_name, None)
    return cost if cost else 0


def _calc_totals(cost):
    ext_cost_total = 0
    for k, v in cost['detail'].items():
        ext_cost_total += v['ext_cost']

    for d in cost['disks']:
        ext_cost_total += d['size'] * cost['detail']['disk']['unit_cost'] * d[
            'multiplier']

    for a in cost['apps']:
        ext_cost_total += a['ext_cost']

    for p in cost['params']:
        ext_cost_total += p['ext_cost']

    if cost['os_build']:
        ext_cost_total += cost['os_build']['ext_cost']

    cost['totals'] = {
        'ext_cost': ext_cost_total,
        'ext_cost_display': render_rate(ext_cost_total)
    }


def _update_detail_costs(cost, server):
    cbhook = get_rate_hook(server.group, server.environment,
                           server.resource_handler.resource_technology)
    if cbhook:
        for k, v in cost['detail'].items():
            v['unit_cost'] = 0
            v['unit_cost_display'] = render_rate(0)

        cost['detail']['custom'] = {
            'unit_cost': server.hw_rate,
            'unit_cost_display': render_rate(server.hw_rate),
            'qty': 1,
            'ext_cost': server.hw_rate,
            'ext_cost_display': render_rate(server.hw_rate)
        }
    else:
        for k, v in cost['detail'].items():
            v['ext_cost'] = v['unit_cost'] * v['qty']
            v['unit_cost_display'] = render_rate(v['unit_cost'])
            v['ext_cost_display'] = render_rate(v['ext_cost'])


def _update_disks(cost, server):
    for disk in server.disks.all():
        unit_cost = cost['detail']['disk']['unit_cost']
        multiplier = 1
        storage_type = ''

        if disk.disk_storage:
            storage_type = disk.disk_storage.type
            if storage_type and storage_type.disktypemultiplier_set:
                disk_type_multiplier = storage_type.disktypemultiplier_set.first()
                if disk_type_multiplier:
                    multiplier = disk_type_multiplier.multiplier

        cost['disks'].append({
            'name': '{} ({})'.format(disk.name,
                                     storage_type) if storage_type else disk.name,
            'size': disk.disk_size,
            'multiplier': multiplier,
            'ext_cost_display': render_rate(
                unit_cost * disk.disk_size * multiplier)
        })


def _update_osbuild_rate(cost, server):
    osb = server.os_build
    if not osb:
        # No OS Build is set on this server.
        return

    osb_rate = osb.osbuildrate_set.filter(
        environment=server.environment).first()
    if not osb_rate:
        osb_rate = osb.osbuildrate_set.filter(environment=None).first()

    if osb_rate and osb_rate.rate:
        rate = osb_rate.rate
    else:
        # There's no rate associated with this OS Build for this
        # environment/globally
        return

    cost['os_build'] = {
        'name': osb.name,
        'qty': 1,
        'unit_cost': rate,
        'ext_cost': rate * 1,
        'unit_cost_display': render_rate(rate),
        'ext_cost_display': render_rate(rate * 1)
    }


def _update_app_rates(cost, server):
    for app in server.applications.all():
        rate = 0

        app_rate = app.applicationrate_set.filter(
            environment=server.environment).first()
        if not app_rate:
            app_rate = app.applicationrate_set.filter(environment=None).first()

        if app_rate:
            rate = app_rate.rate

        if not rate or rate == 0:
            continue

        cost['apps'].append({
            'name': app.name,
            'qty': 1,
            'unit_cost': rate,
            'unit_cost_display': render_rate(rate),
            'ext_cost': 1 * rate,
            'ext_cost_display': render_rate(1 * rate),
        })


def _update_param_rates(cost, server):
    for param in server.custom_field_values.all():
        rate = 0

        cfv_rate = param.field.customfieldrate_set.filter(
            environment=server.environment).first()
        if not cfv_rate:
            cfv_rate = param.field.customfieldrate_set.filter(
                environment=None).first()

        if cfv_rate:
            rate = cfv_rate.rate

        if not rate or rate == 0:
            continue

        cost['params'].append({
            'name': param.field.label,
            'qty': 1,
            'unit_cost': rate,
            'unit_cost_display': render_rate(rate),
            'ext_cost': 1 * rate,
            'ext_cost_display': render_rate(1 * rate)
        })
