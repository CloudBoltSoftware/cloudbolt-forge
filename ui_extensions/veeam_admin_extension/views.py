from datetime import datetime

from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import boto3
import json

from cbhooks.models import CloudBoltHook
from extensions.views import admin_extension, tab_extension, TabExtensionDelegate
from infrastructure.models import CustomField, Server, Environment
from tabs.views import TabGroup
from utilities.decorators import dialog_view
from utilities.logger import ThreadLogger
from utilities.permissions import cbadmin_required
from utilities.templatetags import helper_tags

from xui.veeam.forms import AzureRestoreForm, VeeamEndpointForm, EC2RestoreForm
from xui.veeam.veeam_admin import VeeamManager

logger = ThreadLogger(__name__)


class VeeamDelegate(TabExtensionDelegate):
    def should_display(self):
        veeam = VeeamManager()
        if not veeam.get_connection_info():
            return False
        return True


@dialog_view
def take_backup(request, server_id):
    server = Server.objects.get(id=server_id)
    if request.method == 'GET':
        content = _("Are you sure you want to take a backup for this server?")
        return {
            'title': _("Take Backup"),
            'content': content,
            'use_ajax': True,
            'action_url': '/veeam/take_backup/{server_id}/'.format(server_id=server_id),
            'submit': _("Take"),
        }
    if request.method == 'POST':
        veeam_manager = VeeamManager()
        try:
            take_backup_action = CloudBoltHook.objects.get(name="Take Veeam Backup")
        except Exception:
            veeam_manager.setup_take_backup_action()
            take_backup_action = CloudBoltHook.objects.get(name="Take Veeam Backup")

        install_job = take_backup_action.run_as_job(server=server)[0]
        messages.success(request,
                         mark_safe(f"<a href='{install_job.get_absolute_url()}'>Job</a> to take backup started"))

    return HttpResponseRedirect(reverse('server_detail', args=[server_id]))


@dialog_view
def restore_backup(request, server_id, restore_point_href):
    server = Server.objects.get(id=server_id)
    if request.method == 'GET':
        content = _("Are you sure you want to restore this backup?")
        return {
            'title': _("Restore Backup"),
            'content': content,
            'use_ajax': True,
            'action_url': '/veeam/restore_backup/{server_id}/{restore_point}/'.format(restore_point=restore_point_href,
                                                                                      server_id=server_id),
            'submit': _("Restore"),
        }

    if request.method == 'POST':
        veeam_manager = VeeamManager()
        try:
            restore_backup_action = CloudBoltHook.objects.get(name="Restore Veeam Backup")
        except Exception:
            veeam_manager.setup_restore_backup_action()
            restore_backup_action = CloudBoltHook.objects.get(name="Restore Veeam Backup")

        install_job = restore_backup_action.run_as_job(server=server, restore_point_href=restore_point_href)[0]
        messages.success(request,
                         mark_safe(f"<a href='{install_job.get_absolute_url()}'>Job</a> to restore backup started"))

    return HttpResponseRedirect(reverse('server_detail', args=[server_id]))


@dialog_view
@cbadmin_required
def edit_veeam_endpoint(request, endpoint_id=None):
    """
    Create and edit dialog for a RH's NSX endpoint.
    If `endpoint_id` is None,
    """
    endpoint = VeeamManager().get_connection_info()
    action_url = reverse('create_veeam_endpoint')
    if endpoint or endpoint_id:
        action_url = reverse('edit_veeam_endpoint', args=[endpoint.id])
    if request.method == 'POST':
        form = VeeamEndpointForm(request.POST, instance=endpoint)
        if form.is_valid():
            form.save()
            msg = "The Veeam Server Management Endpoint settings have been saved."
            messages.success(request, msg)
            profile = request.get_user_profile()
            logger.info("Endpoint set to {} by {}.".format(endpoint, profile.user.username))
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = VeeamEndpointForm(instance=endpoint)

    return {
        'title': 'Modify Veeam Server Management Endpoint Settings',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "Veeam Server Management Endpoint, Used to support advanced backup and restoration actions",
        'submit': 'Save',
    }


@dialog_view
@cbadmin_required
def delete_veeam_endpoint(request):
    endpoint = VeeamManager().get_connection_info()
    if request.method == 'POST':
        endpoint.delete()
        msg = "The Veeam Server Endpoint has been deleted."
        messages.success(request, msg)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    return {
        'title': 'Remove Veeam Server Manager Endpoint?',
        'content': 'Are you sure you want to delete Veeam Server endpoint \'{}\'?'.format(endpoint),
        'use_ajax': True,
        'action_url': reverse('delete_veeam_endpoint'),
        'submit': 'Remove'
    }


@dialog_view
@cbadmin_required
def verify_veeam_endpoint(request):
    veeam = VeeamManager()
    endpoint = veeam.get_connection_info()
    if not endpoint:
        messages.warn(
            request, "No Veeam Endpoint found! Nothing to verify")
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    try:
        veeam.verify_connection()
    except Exception as err:
        msg = format_html('Could not make a connection to the Veeam Server Manager at'
                          '<b>"{}"</b>:<br>{}', endpoint, str(err))
    else:
        msg = format_html('Successfully connected to the Veeam Server Manager at '
                          '<b>"{}"</b>.', endpoint)

    return {
        'title': 'Verify connection to Veeam Server Manager Endpoint',
        'content': msg,
        'submit': None,
        'cancel': "OK",
    }


@dialog_view
def restore_backup_to_cloud(request, backup_name):
    if request.method == 'GET':
        content = _("Provide the information below to restore to Microsoft Azure.")
        form = AzureRestoreForm()
        return {
            'title': _("Restore Backup"),
            'content': content,
            'form': form,
            'use_ajax': True,
            'action_url': '/veeam/restore_backup_to_cloud/{backup_name}/'.format(backup_name=backup_name),
            'submit': _("Restore"),
        }
    if request.method == 'POST':
        veeam_manager = VeeamManager()
        form = AzureRestoreForm(request.POST)
        if form.is_valid():
            context = {
                'vmname': form.cleaned_data['vm_name'],
                'backup_name': backup_name,
                'network_name': form.cleaned_data['network_name'],
                'vm_size': form.cleaned_data['vm_size'],
                'location': form.cleaned_data['location'],
                'storage_account': form.cleaned_data['storage_account'],
                'resource_group': form.cleaned_data['resource_group'],
            }
            try:
                restore_backup_action = CloudBoltHook.objects.get(name="Restore Veeam Backup To Azure")
            except Exception:
                veeam_manager.setup_restore_backup_to_azure_action()
                restore_backup_action = CloudBoltHook.objects.get(name="Restore Veeam Backup To Azure")

                # Server running this job will be the veeam server. We can find it using the IP address in the
                # connection Info
            ip = veeam_manager.get_connection_info().ip
            try:
                server = Server.objects.get(ip=ip)
            except Exception:
                # No server associated with the connection info IP address exists.
                messages.error(request, "The Veeam server could not be found.")
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

            restore_backup_to_azure_job = restore_backup_action.run_as_job(server=server, script_context=context)[0]
            messages.success(request,
                             mark_safe(
                                 f"<a href='{restore_backup_to_azure_job.get_absolute_url()}'>Job {restore_backup_to_azure_job.id}</a> to restore backup started"))
        else:
            raise Exception(form.errors)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def get_ec2_client(env):
    ec2 = boto3.client('ec2',
                       region_name=env.aws_region,
                       aws_access_key_id=env.resource_handler.serviceaccount,
                       aws_secret_access_key=env.resource_handler.servicepasswd)
    return ec2


def get_aws_vpc(request):
    env_id = request.GET.get('env_id')
    if not env_id:
        return HttpResponse(json.dumps([]))
    env = Environment.objects.get(id=env_id)
    ec2 = get_ec2_client(env)
    vpc_ids = []

    for reservation in ec2.describe_instances().get('Reservations'):
        reservation_instances = reservation.get('Instances')
        for instance in reservation_instances:
            vpc_id = instance.get('VpcId')
            vpc_ids.append(vpc_id)

    return HttpResponse(json.dumps(vpc_ids))


def get_aws_security_groups(request):
    env_id = request.GET.get('env_id')
    if not env_id:
        return HttpResponse(json.dumps([]))
    env = Environment.objects.get(id=env_id)
    ec2 = get_ec2_client(env)
    sg_ids = []

    for SecurityGroup in ec2.describe_security_groups().get('SecurityGroups'):
        group_id = SecurityGroup.get('GroupId')
        sg_ids.append(group_id)

    return HttpResponse(json.dumps(sg_ids))


def get_aws_availability_zones(request):
    env_id = request.GET.get('env_id')
    if not env_id:
        return HttpResponse(json.dumps([]))
    env = Environment.objects.get(id=env_id)
    ec2 = get_ec2_client(env)
    availability_zones = []

    for availability_zone in ec2.describe_availability_zones().get('AvailabilityZones'):
        zone_name = availability_zone.get('ZoneName')
        availability_zones.append(zone_name)

    return HttpResponse(json.dumps(availability_zones))


@dialog_view
def restore_backup_to_ec2_cloud(request, backup_name):
    if request.method == 'GET':
        content = _("Provide the information below to restore to EC2")
        form = EC2RestoreForm()
        return {
            'title': _("Restore Backup"),
            'content': content,
            'form': form,
            'use_ajax': True,
            'action_url': reverse('restore_to_ec2_cloud', kwargs={"backup_name": backup_name}),
            'submit': _("Restore"),
            'extra_onready_js': mark_safe("""
                                        $('#div_id_environment').on('change',(function () {
                                        var env_id = $('#div_id_environment option:selected').val();
                                        $.getJSON('%s?env_id='+env_id, function (vpc_ids) {
                                            var $selectElement = $("#id_vpc_id");
                                            $selectElement.empty();
                                            $.each(vpc_ids, function (key, value) {
                                                $selectElement.append($("<option></option>").attr("value", value).text(value));
                                            });
                                        });
                                        $.getJSON('%s?env_id='+env_id, function (sg_ids) {
                                            var $securityGroupElement = $("#id_sgroup_name");
                                            $securityGroupElement.empty();
                                            $.each(sg_ids, function (key, value) {
                                                $securityGroupElement.append($("<option></option>").attr("value", value).text(value));
                                            });
                                        });
                                        $.getJSON('%s?env_id='+env_id, function (availability_zones) {
                                            var $availabilityZoneElement = $("#id_availability_zone");
                                            $availabilityZoneElement.empty();
                                            $.each(availability_zones, function (key, value) {
                                                $availabilityZoneElement.append($("<option></option>").attr("value", value).text(value));
                                            });
                                        });
                                    })).change();
                            """ % (reverse('get_aws_vpc'), reverse('get_aws_security_groups'),
                                   reverse('get_aws_availability_zones')))
        }
    if request.method == 'POST':
        veeam_manager = VeeamManager()

        form = EC2RestoreForm(request.POST)
        # Since the choices fields have not been declared during form creation, we need to dynamically declare them.
        vpc_id = request.POST.get('vpc_id')
        sgroup_name = request.POST.get('sgroup_name')
        availability_zone = request.POST.get('availability_zone')

        form.fields['vpc_id'].choices = [(vpc_id, vpc_id)]
        form.fields['sgroup_name'].choices = [(sgroup_name, sgroup_name)]
        form.fields['availability_zone'].choices = [(availability_zone, availability_zone)]

        if form.is_valid():
            environment = form.cleaned_data['environment']
            env = Environment.objects.get(id=environment)
            resource_handler = env.resource_handler

            context = {
                'vm_name': form.cleaned_data['vm_name'],
                'environment': environment,
                'backup_name': backup_name,
                'amazon_access_key': resource_handler.serviceaccount,
                'region_name': env.aws_region,
                'region_type': form.cleaned_data['region_type'],
                'disk_type': form.cleaned_data['disk_type'],
                'instance_type': form.cleaned_data['instance_type'],
                'license_type': form.cleaned_data['license_type'],
                'vpc_id': form.cleaned_data['vpc_id'],
                'sgroup_name': form.cleaned_data['sgroup_name'],
                'reason': form.cleaned_data['reason'],
                'availability_zone': form.cleaned_data['availability_zone'],
            }
            try:
                restore_backup_action = CloudBoltHook.objects.get(name="Restore Veeam Backup To EC2")
            except Exception:
                veeam_manager.setup_restore_backup_to_ec2__action()
                restore_backup_action = CloudBoltHook.objects.get(name="Restore Veeam Backup To EC2")

            # Server running this job will be the veeam server. We can find it using the IP address in the connection Info
            ip = veeam_manager.get_connection_info().ip
            try:
                server = Server.objects.get(ip=ip)
            except Exception as error:
                # No server associated with the connection info IP address exists.
                messages.error(request, "The Veeam server could not be found.")
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

            restore_backup_job = restore_backup_action.run_as_job(server=server, script_context=context)[0]
            messages.success(request,
                             mark_safe(
                                 f"<a href='{restore_backup_job.get_absolute_url()}'>Job {restore_backup_job.id}</a> to restore backup started"))
        else:
            raise Exception(form.errors)

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@dialog_view
def install_agent(request, server_id):
    server = Server.objects.get(id=server_id)
    veeam = VeeamManager()
    if request.method == 'GET':
        content = _(
            "Are you sure you want to install Veeam Agent on this server?")
        return {
            'title': _("Install Agent?"),
            'content': content,
            'use_ajax': True,
            'action_url': '/veeam/install_agent/{server_id}/'.format(server_id=server_id),
            'submit': _("Install"),
        }
    if request.method == 'POST':
        try:
            install_agent_action = CloudBoltHook.objects.get(name="Install Veeam Agent")
        except Exception:
            veeam.setup_veeam_install_agent_action()
            install_agent_action = CloudBoltHook.objects.get(name="Install Veeam Agent")
        install_job = install_agent_action.run_as_job(server=server)[0]
        messages.success(request, mark_safe(
            f"<a href='{install_job.get_absolute_url()}'>Job {install_job.id}</a> to install agent " f"started"))

    return HttpResponseRedirect(reverse('server_detail', args=[server_id]))


@dialog_view
def refresh_agent(request, server_id):
    """
    Checks if the server specified has a veeam agent
    """
    veeam = VeeamManager()

    server = Server.objects.get(id=server_id)
    # Start a Job to do the refresh

    server = veeam.refresh_server(server, {'server': server, 'veeam_server': veeam.get_connection_info()})

    if server.veeam_agent_id:
        messages.success(request, "Veeam Agent Found")
    else:
        messages.warning(request, "No Veeam Agent Found")
    return HttpResponseRedirect(reverse('server_detail', args=[server_id]))


@tab_extension(model=Server, title='Veeam', delegate=VeeamDelegate)
def veeam_tab(request, obj_id):
    server = Server.objects.get(id=obj_id)
    veeam = VeeamManager()

    restore_points = veeam.get_restore_points(server.hostname)
    if restore_points:
        restore_points.sort(key=lambda r: datetime.strptime(
            r.get('time'), '%Y-%m-%d %H:%M:%S'), reverse=True)
    is_agent_installed = veeam.should_install_agent(server)

    take_backup_job = server.jobs.filter(job_parameters__hookparameters__hook__name='Take Veeam Backup').last()

    context = {}

    backup_job_running = False
    if take_backup_job:
        if take_backup_job.is_active():
            backup_job_running = True
            context.update({'take_backup_job_url': take_backup_job.get_absolute_url()})
    context.update({'backup_job_running': backup_job_running})

    if not context:
        # Check if server is powered on.
        if server.power_status == 'POWERON':
            # This server has no agent installed
            context.update({'install_agent': False})
            context.update({'power_status': True})
        else:
            context.update({'power_status': False})
            status = 'warning'
            msg = "Veeam might be installed in this server but the server is powered off"

            server_not_powered_on = helper_tags.alert(status, msg)
            context.update(
                {'server_not_powered_on': server_not_powered_on})
    else:
        context.update({'install_agent': True})

    context.update({'server_id': obj_id})
    server_settings_ok = check_server_settings_status(server)

    if not server_settings_ok:
        status = 'warning'
        msg = "Veeam agent is not installed and the server username and password are not correctly setup. This might make it imposible to install the agent on this server from cloudbolt. You can configure them on the Configuration page on the server details tab. "

        server_credentials_not_set = helper_tags.alert(status, msg)
        context.update(
            {'server_credentials_not_set': server_credentials_not_set})

    install_job = server.jobs.filter(job_parameters__hookparameters__hook__name='Install Veeam Agent').last()

    install_job_running = False
    if install_job:
        if install_job.is_active():
            install_job_running = True
            context.update({'job_url': install_job.get_absolute_url()})
    context.update({'job_running': install_job_running})

    restore_job = server.jobs.filter(job_parameters__hookparameters__hook__name='Restore Veeam Backup').last()
    restore_job_running = False
    if restore_job:
        if restore_job.is_active():
            restore_job_running = True
            context.update({'restore_job_url': restore_job.get_absolute_url()})
    context.update({'restore_job_running': restore_job_running})

    context.update({'server': server, 'restore_points': restore_points, 'install_agent': is_agent_installed})
    return render(request, 'veeam/templates/server_tab.html', context)


@admin_extension(title='Veeam Management Integration', description='Admin tab to show available backups and jobs')
def admin_page(request):
    veeam = VeeamManager()
    endpoint = veeam.get_connection_info()
    # If no Connection info, show a dialog for adding a connection info.
    if not endpoint:
        veeam_context = {

            'tabs': TabGroup(
                template_dir='veeam/templates',
                context={},
                request=request,
                tabs=[
                    (_(""), 'dashboard', dict(context={}))
                ],
            )
        }
        return render(request, 'veeam/templates/admin_page.html', veeam_context)

    jobs = veeam.get_jobs()
    backups = veeam.get_backups()
    summary = veeam.get_summary()

    context = {}
    ip = veeam.get_connection_info().ip
    try:
        server = Server.objects.get(ip=ip)
    except Exception:
        messages.error(request, message="The server running Veeam could not be found.")
        return render(request, 'veeam/templates/admin_page.html', {})

    restore_to_ec2_job = server.jobs.filter(
        job_parameters__hookparameters__hook__name='Restore Veeam Backup To EC2').last()

    restore_to_ec2_job_running = False
    if restore_to_ec2_job and restore_to_ec2_job.is_active():
        restore_to_ec2_job_running = True
        context.update({'restore_to_ec2_job_url': restore_to_ec2_job.get_absolute_url()})
    context.update({'restore_to_ec2_job_running': restore_to_ec2_job_running})

    restore_to_azure_job = server.jobs.filter(
        job_parameters__hookparameters__hook__name='Restore Veeam Backup To Azure').last()
    restore_to_azure_job_running = False
    if restore_to_azure_job and restore_to_azure_job.is_active():
        restore_to_azure_job_running = True
        context.update({'restore_to_azure_job_url': restore_to_azure_job.get_absolute_url()})
    context.update({'restore_to_azure_job_running': restore_to_azure_job_running})

    context.update({'jobs': jobs, 'backups': backups, 'endpoint': endpoint})

    veeam_context = {

        'tabs': TabGroup(
            template_dir='veeam/templates',
            context=context,
            request=request,
            tabs=[
                # First tab uses template 'groups/tabs/tab-main.html'
                # (_("Configuration"), 'configuration', {}),
                # Tab 2 is conditionally-shown in this slot and
                # uses template 'groups/tabs/tab-related-items.html'
                (_("Dashboard"), 'dashboard', dict(context=summary)),
                (_("Jobs"), 'jobs', {}),
                (_("Backups"), 'backups', {})
            ],
        )
    }
    return render(request, 'veeam/templates/admin_page.html', veeam_context)


def check_server_settings_status(server):
    # If the server doesn't have username and password,
    # We can't use Connection info to execute a script on it.
    if server.password is None:
        return False
    return True
