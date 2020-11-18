import requests
import time
import json

from django.contrib import messages
from django.utils.html import format_html

from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe

from extensions.views import (TabExtensionDelegate, admin_extension,
                              tab_extension)
from cbhooks.models import CloudBoltHook
from infrastructure.models import CustomField, Server
from tabs.views import TabGroup
from utilities.decorators import dialog_view
from utilities.permissions import cbadmin_required

from utilities.templatetags import helper_tags
from utilities.logger import ThreadLogger

from xui.data_dog.forms import DataDogConnectionForm
from xui.data_dog.data_dog_helper import DataDog


logger = ThreadLogger(__name__)

@dialog_view
@cbadmin_required
def add_credentials(request):
    """
    Create credentials for Datadog integration.
    """
    action_url = reverse('add_data_dog_credentials')

    if request.method == 'POST':
        form = DataDogConnectionForm(request.POST)
        if form.is_valid():
            form.save()
            msg = "The Datadog credentials have been saved."
            messages.success(request, msg)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = DataDogConnectionForm()

    return {
        'title': 'Add Datadog connection credentials',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "Datadog credentials",
        'submit': 'Save',
    }


@dialog_view
@cbadmin_required
def edit_credentials(request, endpoint_id=None):
    """
    Edit data dog connection credentials
    """
    credentials = DataDog().get_connection_info()
    action_url = reverse('edit_data_dog_credentials')
    if request.method == 'POST':
        form = DataDogConnectionForm(request.POST, instance=credentials)
        if form.is_valid():
            form.save()
            msg = "The Datadog credentials have been updated."
            messages.success(request, msg)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = DataDogConnectionForm(initial={
            'ip': credentials.ip, 'headers': credentials.headers, 'protocol': credentials.protocol})

    return {
        'title': 'Edit Datadog connection credentials',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "Datadog credentials",
        'submit': 'Save',
    }


@dialog_view
@cbadmin_required
def delete_credentials(request):
    data_dog_ci = DataDog().get_connection_info()
    if request.method == 'POST':
        data_dog_ci.delete()
        msg = "The Datadog credentials have been deleted."
        messages.success(request, msg)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    return {
        'title': 'Remove Datadog Credentials?',
        'content': 'Are you sure you want to delete these Datadog credentials?',
        'use_ajax': True,
        'action_url': reverse('delete_data_dog_credentials'),
        'submit': 'Remove'
    }


@dialog_view
@cbadmin_required
def verify_credentials(request):
    data_dog = DataDog()

    status, reason = data_dog.verify_connection()
    if status:
        msg = format_html('Successfully connected to Datadog')
    else:
        msg = format_html(
            f'Could not make a connection to Datadog. Reason: {reason}')

    return {
        'title': 'Verify connection to Datadog credentials',
        'content': msg,
        'submit': None,
        'cancel': "OK",
    }


@admin_extension(title='Datadog Integration', description='Datadog Integration into CloudBolt')
def admin_page(request):
    data_dog = None
    hosts = []
    try:
        data_dog = DataDog()
        api_key = data_dog.get_api_key()
        app_key = data_dog.get_app_key()
        url = data_dog.generate_url("hosts")
        response = requests.get(url,
                                params={
                                    'api_key': api_key,
                                    'application_key': app_key
                                })
        res = response.json()
        for host in res['host_list']:
            res_dict = {}
            res_dict['name'] = host['name']
            res_dict['os'] = host['meta']['platform']
            res_dict['sources'] = host['sources']
            res_dict['up'] = host['up']
            res_dict['ipaddress'] = json.loads(host['meta']['gohai'])['network']['ipaddress']
            res_dict['agent_version'] = host['meta']['agent_version']
            server = Server.objects.filter(hostname__icontains=host['name'], ip=res_dict['ipaddress']).first()
            if server is not None:
                res_dict['server_url'] = server.get_absolute_url()
            hosts.append(res_dict)
    except Exception:
        pass

    data_dog_context = {

        'tabs': TabGroup(
            template_dir='data_dog/templates',
            request=request,
            tabs=[
                (_("Dashboard"), 'dashboard', dict(
                    context={"data_dog_ci": data_dog.get_connection_info()})),
                (_("Servers"), 'servers', dict(
                    context={"res": hosts})),
            ],
        )
    }
    return render(request, 'data_dog/templates/admin_page.html', data_dog_context)


class DataDogTabDelegate(TabExtensionDelegate):
    def should_display(self):
        data_dog = DataDog()
        try:
            data_dog.get_api_key()
            data_dog.get_app_key()
        except Exception:
            return False
        return True


@dialog_view
def install_agent(request, server_id):
    if request.method == 'GET':
        content = _(
            "Are you sure you want to install Datadog Agent on this server?")
        return {
            'title': _("Install Agent?"),
            'content': content,
            'use_ajax': True,
            'action_url': reverse('install_data_dog_agent', args=[server_id]),
            'submit': _("Install"),
        }
    if request.method == 'POST':
        server = Server.objects.get(id=server_id)
        data_dog = DataDog()
        try:
            install_agent_action = CloudBoltHook.objects.get(name="Install DataDog Agent")
        except Exception:
            data_dog.setup_data_dog_install_agent_action()
            install_agent_action = CloudBoltHook.objects.get(name="Install DataDog Agent")
        install_job = install_agent_action.run_as_job(server=server)[0]
        messages.success(request,
                         mark_safe(f"<a href='{install_job.get_absolute_url()}'>Job</a> to install agent started"))

    return HttpResponseRedirect(request.META['HTTP_REFERER'])


@dialog_view
def uninstall_agent(request, server_id):
    if request.method == 'GET':
        content = _(
            "Are you sure you want to uninstall Datadog Agent from this server?")
        return {
            'title': _("Uninstall Agent?"),
            'content': content,
            'use_ajax': True,
            'action_url': reverse('uninstall_datadog_agent', args=[server_id]),
            'submit': _("Uninstall"),
        }
    if request.method == 'POST':
        server = Server.objects.get(id=server_id)
        datadog_manager = DataDog()
        try:
            uninstall_agent_action = CloudBoltHook.objects.get(name="UnInstall Datadog Agent")
        except Exception:
            datadog_manager.setup_data_dog_uninstall_agent_action()
            uninstall_agent_action = CloudBoltHook.objects.get(name="UnInstall Datadog Agent")
        install_job = uninstall_agent_action.run_as_job(server=server)[0]
        messages.success(request,
                         mark_safe(f"<a href='{install_job.get_absolute_url()}'>Job</a> to uninstall agent started"))

        return HttpResponseRedirect(request.META['HTTP_REFERER'])

def get_datadog_actions():
    return ["Uninstall Agent"]


@tab_extension(model=Server,
               title='Datadog',
               description='Datadog Server Tab',
               delegate=DataDogTabDelegate)
def server_tab_data_dog(request, obj_id=None):
    data_dog = DataDog()
    context = {}
    CustomField.objects.get_or_create(
        name='datadog_installed', type='BOOL',
        defaults={'label': 'Is Datadog Agent Installed',
                  'show_as_attribute': False})

    api_key = data_dog.get_api_key()
    app_key = data_dog.get_app_key()

    server = get_object_or_404(Server, pk=obj_id)

    now = int(time.time())
    time_from = now - 3600

    # Queries
    # Datadog automatically truncates a server name to 15 characters.
    # For the truncation, it only happens for windows machines
    if server.is_windows():
        hostname = server.hostname[:15]
    else:
        hostname = server.hostname
    cpu_idle = f"system.cpu.idle{'{host:'}{hostname}{'}'}"
    cpu_io_wait = f"system.cpu.iowait{'{host:'}{hostname}{'}'}"

    free_ram_query = f"system.mem.free{'{host:'}{hostname}{'}'}"
    total_ram_query = f"system.mem.total{'{host:'}{hostname}{'}'}"
    paged_memory = f"system.mem.paged{'{host:'}{hostname}{'}'}"

    total_disk_space_query = f"system.disk.total{'{host:'}{hostname}{'}'}"
    used_disk_space_query = f"system.disk.used{'{host:'}{hostname}{'}'}"
    free_disk_query = f"system.disk.free{'{host:'}{hostname}{'}'}"
    disk_in_use_query = f"system.disk.in_use{'{host:'}{hostname}{'}'}"
    disk_write_time = f"system.disk.write_time_pct{'{host:'}{hostname}{'}'}"

    url = data_dog.generate_url("query")

    queries = [cpu_idle, cpu_io_wait, free_ram_query,
               total_ram_query, total_disk_space_query,
               free_disk_query, disk_in_use_query,
               used_disk_space_query, disk_write_time, paged_memory]

    for query in queries:
        response = requests.get(url,
                                params={
                                    'api_key': api_key,
                                    'application_key': app_key,
                                    'from': time_from, 'to': now, 'query': query})
        if response.ok:
            info = response.json()
            if len(info.get('series')) > 0:
                series = info.get('series')[0]
                pointlist = series.get('pointlist')[-1]

                context.update({series.get('metric'): info})

                # cpu operations
                if series.get('metric') == 'system.cpu.idle':
                    points = series.get('pointlist')
                    _pointlist = [[i[0], round(i[1], 2)] for i in points]
                    context.update({'cpu_idle': [
                        {'data': _pointlist, 'name': 'CPU Idle ', 'color': '#153c55', 'type': 'area'}]})

                elif series.get('metric') == 'system.cpu.iowait':
                    points = series.get('pointlist')
                    _pointlist = [[i[0], round(i[1], 2)] for i in points]
                    context.update({'cpu_io_wait': [
                        {'data': _pointlist, 'name': 'CPU IO Wait ', 'color': '#0086AD', 'type': 'area'}]})

                # memory operations
                elif series.get('metric') == 'system.mem.free':
                    free_ram = pointlist[-1] / 1e9
                    context.update({'free_ram': round(free_ram, 1)})
                    points = series.get('pointlist')
                    _pointlist = [[i[0], round(i[1] / 1e9, 2)] for i in points]
                    context.update({'free_memory_series': [
                        {'data': _pointlist, 'name': 'Free Memory ', 'color': '#666666', 'type': 'area'}]})

                elif series.get('metric') == 'system.mem.paged':
                    points = series.get('pointlist')
                    _pointlist = [[i[0], round(i[1] / 1e9, 2)] for i in points]
                    context.update({'paged_memory': [
                        {'data': _pointlist, 'name': 'Paged Memory', 'color': '#FF901F', 'type': 'area'}]})

                # disk operations
                if series.get('metric') == 'system.disk.used':
                    disk_used = pointlist[-1] / 1e9
                    context.update({'disk_used': round(disk_used)})
                    points = series.get('pointlist')
                    _pointlist = [[i[0], round(i[1] / 1e9, 2)] for i in points]
                    context.update({'disk_used_series': [
                        {'data': _pointlist, 'name': 'Disk Used', 'color': '#0069cf', 'type': 'area'}]})

                elif series.get('metric') == 'system.disk.free':
                    free_disk = pointlist[-1] / 1e9
                    context.update({'free_disk': round(free_disk)})

                elif series.get('metric') == 'system.disk.write_time_pct':
                    points = series.get('pointlist')
                    context.update({'disk_write_time': [
                        {'data': points, 'name': 'Disk Write Time', 'color': '#B6A959', 'type': 'area'}]})

    if not context:
        # Check if server is powered on.
        if server.power_status == 'POWERON':
            # This server has no agent installed
            context.update({'agent_installed': False})
            context.update({'power_status': True})
        else:
            context.update({'power_status': False})
            status = 'warning'
            msg = "Datadog might be installed in this server but the server is powered off"

            server_not_powered_on = helper_tags.alert(status, msg)
            context.update(
                {'server_not_powered_on': server_not_powered_on})
    else:
        # Since some servers might have agents not installed from coudbolt,
        # their datadog_installed value will be none. We can update this to True.
        # If the agent has been uninstalled, the datadog_installed value will be False.
        if server.datadog_installed == None:
            server.datadog_installed = True
        server.save()
        context.update({'agent_installed': True})

    context.update({'server_id': obj_id})
    server_settings_ok = check_server_settings_status(server)
    if not server_settings_ok:
        status = 'warning'
        msg = "Datadog agent is not installed and the server username and password are not correctlty setup. This might make it imposible to install the agent on this server from cloudbolt. You can configure them on the Configuration page on the server details tab. "

        server_credentials_not_set = helper_tags.alert(status, msg)
        context.update(
            {'server_credentials_not_set': server_credentials_not_set})
    install_job = server.jobs.filter(job_parameters__hookparameters__hook__name='Install DataDog Agent').last()
    uninstall_job = server.jobs.filter(job_parameters__hookparameters__hook__name='UnInstall Datadog Agent').last()
    job_running = False
    uninstall_job_running = False

    if install_job:
        if install_job.is_active():
            job_running = True
            context.update({'job_url': install_job.get_absolute_url()})
    if uninstall_job and uninstall_job.is_active():
        uninstall_job_running = True
        context.update({'uninstall_job_url': uninstall_job.get_absolute_url()})

    if not context.get('agent_installed') and server.datadog_installed:
        context.update({'waiting_for_metrics': True})

    context.update({'job_running': job_running,
                    'uninstall_job_running': uninstall_job_running,
                    'datadog_actions': get_datadog_actions(),
                    'datadog_installed': server.datadog_installed
                    })
    return render(request, 'data_dog/templates/data_dog_server_tab.html', context)


def check_server_settings_status(server):
    # If the server doesn't have username and password,
    # We can't use Connection info to execute a script on it.
    if server.password is None:
        return False
    return True
