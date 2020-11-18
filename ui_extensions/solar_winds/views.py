from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.urls import reverse
from django.shortcuts import render
from django.utils.safestring import mark_safe

from extensions.views import (TabExtensionDelegate, admin_extension,
                              tab_extension)
from tabs.views import TabGroup
from utilities.permissions import cbadmin_required

from utilities.decorators import dialog_view
from infrastructure.models import CustomField, Server
from cbhooks.models import CloudBoltHook

from xui.solar_winds.forms import SolarWindsConectionForm, SolarWindsServerConectionForm
from xui.solar_winds.solar_winds_helper import SolarWindsManager


class SolarWindsDelegate(TabExtensionDelegate):
    def should_display(self):
        solar_winds = SolarWindsManager()
        if solar_winds.get_connection_info():
            return True
        return False

@dialog_view
@cbadmin_required
def verify_credentials(request):
    solar_winds = SolarWindsManager()
    response = solar_winds.verify_rest_credentials()

    if response:
        msg = format_html('Successfully connected to SolarWinds')
    else:
        msg = format_html(
            'Could not make a connection to SolarWinds with this API Key')

    return {
        'title': 'Verify connection to SolarWinds credentials',
        'content': msg,
        'submit': None,
        'cancel': "OK",
    }


@dialog_view
@cbadmin_required
def verify_server_credentials(request):
    solar_winds = SolarWindsManager()
    response = solar_winds.verify_server_connection()
    if not response[0]:
        msg = format_html(response[1])
    msg = format_html("Connection to the solar winds server succesful")

    return {
        'title': 'Verify connection to SolarWinds credentials',
        'content': msg,
        'submit': None,
        'cancel': "OK",
    }


@dialog_view
@cbadmin_required
def add_credentials(request):
    """
    Create credentials for SolarWinds integration.
    """
    action_url = reverse('add_credentials')
    if request.method == 'POST':
        form = SolarWindsConectionForm(request.POST)
        if form.is_valid():
            form.save()
            msg = "The SolarWinds credentials have been saved."
            messages.success(request, msg)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = SolarWindsConectionForm()

    return {
        'title': 'Add SolarWinds Connection Info Rest',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "SolarWinds credentials",
        'submit': 'Save',
    }


@dialog_view
@cbadmin_required
def add_server_credentials(request):
    """
    Create SolarWinds server credentials.
    """
    action_url = reverse('add_server_credentials')
    if request.method == 'POST':
        form = SolarWindsServerConectionForm(request.POST)
        if form.is_valid():
            form.save()
            msg = "The SolarWinds server credentials have been saved."
            messages.success(request, msg)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = SolarWindsServerConectionForm()

    return {
        'title': 'Add SolarWinds server Connection Info',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "SolarWinds server credentials",
        'submit': 'Save',
    }


@dialog_view
@cbadmin_required
def edit_credentials(request):
    """
    Edit SolarWinds Connection Info Rest
    """
    solar_winds = SolarWindsManager()
    credentials = solar_winds.get_solar_winds_rest_ci()
    action_url = reverse('edit_credentials')
    if request.method == 'POST':
        form = SolarWindsConectionForm(request.POST, instance=credentials)
        if form.is_valid():
            form.save()
            msg = "The SolarWinds credentials have been updated."
            messages.success(request, msg)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = SolarWindsConectionForm(initial={
            'ip': credentials.ip, 'port': credentials.port, 'protocol': credentials.protocol,
            'username': credentials.username, 'password': credentials.password})

    return {
        'title': 'Edit SolarWinds Connection Info Rest',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "SolarWinds credentials",
        'submit': 'Save',
    }


@dialog_view
@cbadmin_required
def edit_server_credentials(request, endpoint_id=None):
    """
    Edit SolarWinds server Connection Info
    """
    solar_winds = SolarWindsManager()
    credentials = solar_winds.get_solar_winds_server_ci()
    action_url = reverse('edit_server_credentials')
    if request.method == 'POST':
        form = SolarWindsServerConectionForm(
            request.POST, instance=credentials)
        if form.is_valid():
            form.save()
            msg = "The SolarWinds server credentials have been updated."
            messages.success(request, msg)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = SolarWindsServerConectionForm(initial={
            'ip': credentials.ip, 'username': credentials.username, 'password': credentials.password})

    return {
        'title': 'Edit SolarWinds server Connection Info',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "SolarWinds server credentials",
        'submit': 'Save',
    }


@dialog_view
@cbadmin_required
def delete_credentials(request):
    solar_winds = SolarWindsManager()
    solar_winds_ci = solar_winds.get_solar_winds_rest_ci()
    if request.method == 'POST':
        solar_winds_ci.delete()
        msg = "The SolarWinds credentials have been deleted."
        messages.success(request, msg)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    return {
        'title': 'Remove SolarWinds Credentials?',
        'content': 'Are you sure you want to delete these SolarWinds credentials?',
        'use_ajax': True,
        'action_url': reverse('delete_credentials'),
        'submit': 'Remove'
    }


@dialog_view
@cbadmin_required
def delete_server_credentials(request):
    solar_winds_ci = SolarWindsManager().get_solar_winds_server_ci()
    if request.method == 'POST':
        solar_winds_ci.delete()
        msg = "The SolarWinds server credentials have been deleted."
        messages.success(request, msg)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    return {
        'title': 'Remove SolarWinds server Credentials?',
        'content': 'Are you sure you want to delete these SolarWinds server credentials?',
        'use_ajax': True,
        'action_url': reverse('delete_server_credentials'),
        'submit': 'Remove'
    }


@admin_extension(title='SolarWinds Integration', description='SolarWinds Integration into CloudBolt')
def admin_page(request):
    solar_winds_manager = SolarWindsManager()
    try:
        solar_winds_ci = solar_winds_manager.get_solar_winds_rest_ci()
    except Exception:
        solar_winds_ci = None

    try:
        solar_winds_server_ci = solar_winds_manager.get_solar_winds_server_ci()
    except Exception:
        solar_winds_server_ci = None

    nodes = solar_winds_manager.get_solar_winds_nodes()
    if nodes:
        for node in nodes:
            server = Server.objects.filter(
                hostname__icontains=node.get('NodeName'), ip=node.get('IPAddress')).first()
            if server:
                node['environment'] = server.environment.name
                node['server_url'] = server.get_absolute_url()

    solar_winds_context = {
        'tabs': TabGroup(
            template_dir='solar_winds/templates',
            request=request,
            tabs=[
                (_("Overview"), 'dashboard', dict(
                    context={"solar_winds_ci": solar_winds_ci, "solar_winds_server_ci": solar_winds_server_ci})),
                (_("Servers"), 'servers', dict(
                    context={'nodes': nodes}))
            ],
        )
    }
    return render(request, 'solar_winds/templates/admin_page.html', solar_winds_context)


@dialog_view
def install_agent(request, server_id):
    if request.method == 'GET':
        content = _(
            "Are you sure you want to install SolarWinds Agent on this server?")
        return {
            'title': _("Install Agent?"),
            'content': content,
            'use_ajax': True,
            'action_url': reverse('install_sam_agent', args=[server_id]),
            'submit': _("Install"),
        }
    if request.method == 'POST':
        solar_winds = SolarWindsManager()
        try:
            install_agent_action = CloudBoltHook.objects.get(name="Install SolarWinds Agent")
        except Exception:
            solar_winds.setup_solar_winds_install_agent_action()
            install_agent_action = CloudBoltHook.objects.get(name="Install SolarWinds Agent")

        server = Server.objects.get(id=server_id)
        install_job = install_agent_action.run_as_job(server=server)[0]
        messages.success(request, mark_safe(f"<a href='{install_job.get_absolute_url()}'>Job</a> to install agent "
                                            f"started"))
        server.solar_winds_not_installed = False

    return HttpResponseRedirect(reverse('server_detail', args=[server_id]))


@tab_extension(model=Server, title='SolarWinds', delegate=SolarWindsDelegate)
def solar_winds_tab(request, obj_id):
    server = Server.objects.get(id=obj_id)
    solar_winds_manager = SolarWindsManager()
    agent_installed = solar_winds_manager.is_agent_installed(server_ip=server.ip)

    is_agent_installed = False

    if agent_installed[-1] not in ['Not Installed', 'Installed']:
        # An error occurred while making the request.
        messages.error(request, f'The following error occurred while making the request to the solarwinds server: {agent_installed[-1]}')
    if agent_installed[0]:
        is_agent_installed = True

    server_stats = {}
    response = solar_winds_manager.get_server_stat(server.ip)
    if response[0]:
        server_stats = response[1]
        server_stats['TotalMemory'] = str(server_stats['TotalMemory']/1e9)[:1]
        server_stats['MemoryUsed'] = str(server_stats['MemoryUsed']/1e9)[:1]
        server_stats['CpuCount'] = server_stats['CpuCount']

        # Load metrics
        cpu_metrics = solar_winds_manager.get_cpu_load_metrics(server.ip)
        memory_used_metrics = solar_winds_manager.get_memory_used_metrics(server.ip)
        network_latency_metrics = solar_winds_manager.get_network_latency_metrics(server.ip)
        server_stats['cpu_load'] = [
                        {'data': cpu_metrics, 'name': 'CPU Load ', 'color': '#153c55', 'type': 'area'}]
        server_stats['memory_used_metrics'] = [
                        {'data': memory_used_metrics, 'name': 'Memory Used', 'color': '#228B22', 'type': 'area'}]
        server_stats['network_latency_metrics'] = [
            {'data': network_latency_metrics, 'name': 'Network Latency', 'color': '#00AEEF', 'type': 'area'}]

    install_job = server.jobs.filter(job_parameters__hookparameters__hook__name='Install SolarWinds Agent').last()

    context = {}
    job_running = False
    if install_job:
        if install_job.is_active():
            job_running = True
            context.update({'job_url': install_job.get_absolute_url()})
    context.update({'job_running': job_running})

    context.update({'is_license_valid': solar_winds_manager.is_license_valid()})

    context.update({'server': server, 'is_agent_installed': is_agent_installed, 'server_stats': server_stats})
    return render(request, 'solar_winds/templates/server_tab.html', context)
