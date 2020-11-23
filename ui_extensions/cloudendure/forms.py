from django import forms
from common.forms import C2Form
from utilities.forms import ConnectionInfoForm
from xui.cloudendure.cloudendure_admin import CloudEndureManager


class CloudEndureConnectionForm(ConnectionInfoForm):
    protocol = forms.ChoiceField(
        choices=[('http', 'HTTP'), ('https', 'HTTPS')], label='Protocol')

    def __init__(self, *args, **kwargs):
        super(CloudEndureConnectionForm, self).__init__(*args, **kwargs)

        self.fields["name"].widget = forms.HiddenInput()
        self.fields["name"].initial = "CloudEndure Endpoint"
        if not self.initial_instance:
            self.fields["protocol"].initial = "https"
            self.fields["port"].initial = "443"

        # Remove connection info fields we do not need in CloudEndure credentials
        del self.fields['ssh_key']
        del self.fields["use_auth_headers"]
        del self.fields["headers"]

        # mark all fields as required
        for field in list(self.fields.values()):
            field.required = True

    def save(self, *args, **kwargs):
        credentials = super(CloudEndureConnectionForm,
                            self).save(*args, **kwargs)
        return credentials

    def clean(self):

        ce = CloudEndureManager()
        if not ce.verify_connection(
            self.cleaned_data.get('protocol'),
            self.cleaned_data.get('ip'),
            self.cleaned_data.get('username'),
            self.cleaned_data.get('port'),
            self.cleaned_data.get('password'),
        ):
            raise forms.ValidationError(
                "Unable to connect to CloudEndure Management Endpoint using the parameters provided ")

        return self.cleaned_data


class CloudEndureProjectSelectForm(C2Form):
    cemanager = CloudEndureManager()
    my_projects = cemanager.get_all_projects()

    # get a tuple of all projects
    projects_tuple = [(name, name) for name in iter(my_projects)]
    project = forms.ChoiceField(choices=projects_tuple, label='Select Project')


class CloudEndureProjectNameForm(C2Form):
    cemanager = CloudEndureManager()
    all_clouds = cemanager.get_all_clouds()
    cloud = forms.ChoiceField(choices=all_clouds, label='Target Cloud')
    project_name = forms.CharField(label="Project Name")
    public_key = forms.CharField(label="AWS Access Key")
    private_key = forms.CharField(label="AWS Access Key Secret")


class CloudEndureLaunchTypeForm(C2Form):
    launch_types = ["TEST", "RECOVERY", "CUTOVER", "DEBUG"]
    launch_type = forms.ChoiceField(
        choices=[(launch, launch) for launch in launch_types], label='Launch Type')
