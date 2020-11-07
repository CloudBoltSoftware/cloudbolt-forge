from django import forms
from django.utils.translation import ugettext as _

from common.forms import C2Form
from infrastructure.models import CustomField, Namespace, Server, Environment, ResourceHandler
from utilities.logger import ThreadLogger
from utilities.forms import ConnectionInfoForm

from .veeam_choices import instance_types, region_types, disk_types, license_types

logger = ThreadLogger(__name__)


def get_aws_environments():
    environments = []
    envs = Environment.objects.filter(resource_handler__resource_technology__name="Amazon Web Services")
    for env in envs:
        if env.aws_region:
            environments.append((env.id, env.name + " " + env.aws_region))
    return environments


class ClientForm(C2Form):
    server_id = forms.CharField(widget=forms.widgets.HiddenInput())
    dns_name_or_ip = forms.CharField(max_length=256,
                                     required=True)
    user_name = forms.CharField(max_length=256,
                                required=True)
    password = forms.CharField(widget=forms.PasswordInput())

    def save(self, profile):
        server_id = self.cleaned_data['server_id']
        host = self.cleaned_data['host']
        user_name = self.cleaned_data['user_name']
        password = self.cleaned_data['password']
        server = Server.objects.get(id=server_id)

        msg = _("Added a new client to '{server}'")

        return True, msg.format(server=server.hostname)


class AzureRestoreForm(C2Form):
    vm_name = forms.CharField(max_length=15, required=True)
    network_name = forms.CharField(max_length=256, required=True)
    vm_size = forms.CharField(max_length=256, required=True)
    location = forms.CharField(max_length=256, required=True)
    storage_account = forms.CharField(max_length=256, required=True)
    resource_group = forms.CharField(max_length=256, required=True)


class EC2RestoreForm(C2Form):
    environment = forms.ChoiceField(required=True,
                                    choices=get_aws_environments(),
                                    help_text="The configured AWS Environment")
    region_type = forms.ChoiceField(required=True, choices=region_types,
                                    help_text="Specifies the AWS region type")
    vpc_id = forms.ChoiceField(required=True, label="VPC ID",
                               help_text="Specifies the ID of a VPC")
    sgroup_name = forms.ChoiceField(required=True, label="Security Group",
                                    help_text="Specifies the name of security group")
    availability_zone = forms.ChoiceField(required=True,
                                          help_text="Specifies the Availability Zone. "
                                                    "Veeam will return the Amazon VPC "
                                                    "subnet that resides in the specified "
                                                    "Availability Zone")
    disk_type = forms.ChoiceField(required=True, choices=disk_types,
                                  help_text="Specifies the storage volume type. Veeam "
                                            "Backup & Replication will saves disks of "
                                            "the restored machine as Amazon Elastic "
                                            "Block Store (EBS) volumes.")

    instance_type = forms.ChoiceField(required=True, choices=instance_types, help_text="Specifies the name of the "
                                                                                       "Amazon EC2 instance type.")
    license_type = forms.ChoiceField(required=True, choices=license_types, help_text="Specifies the OS license.")

    vm_name = forms.CharField(max_length=256, required=True, help_text="The name given to the restored VM")

    reason = forms.CharField(max_length=256, required=True, help_text="Reason for the restoration.")


class VeeamEndpointForm(ConnectionInfoForm):
    protocol = forms.ChoiceField(
        choices=[('http', 'HTTP'), ('https', 'HTTPS')], label='Protocol')

    def __init__(self, *args, **kwargs):
        super(VeeamEndpointForm, self).__init__(*args, **kwargs)

        self.fields["name"].widget = forms.HiddenInput()
        self.fields["name"].initial = "Veeam Server Management Endpoint"
        if not self.initial_instance:
            self.fields["port"].initial = 9399
            self.fields["protocol"].initial = "http"

        # ConnectionInfo has support for ssh key which we don't need for Veeam
        del self.fields['ssh_key']

        del self.fields["use_auth_headers"]
        del self.fields["headers"]

        # mark all fields as required
        for field in list(self.fields.values()):
            field.required = True

    def clean(self):
        try:
            from xui.veeam.veeam_admin import VeeamManager
            veeam = VeeamManager()
            veeam.verify_connection(
                self.cleaned_data.get('protocol'),
                self.cleaned_data.get('ip'),
                self.cleaned_data.get('port'),
                self.cleaned_data.get('username'),
                self.cleaned_data.get('password'),
            )
        except Exception as error:
            raise forms.ValidationError(
                f"Unable to connect to Veeam Server Management Endpoint using the parameters provided due to {error}"
            )

        return self.cleaned_data

    def save(self, *args, **kwargs):
        endpoint = super(VeeamEndpointForm, self).save(*args, **kwargs)
        return endpoint
