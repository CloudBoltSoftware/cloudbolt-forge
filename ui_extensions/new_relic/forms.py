from django import forms
from django.utils.safestring import mark_safe

from utilities.forms import ConnectionInfoForm

from xui.new_relic.new_relic_helper import NewRelicManager


class NewRelicConnectionForm(ConnectionInfoForm):
    protocol = forms.ChoiceField(
        choices=[('http', 'HTTP'), ('https', 'HTTPS')], label='Protocol', initial='https')

    def __init__(self, *args, **kwargs):
        super(NewRelicConnectionForm, self).__init__(*args, **kwargs)
        self.fields["name"].widget = forms.HiddenInput()
        self.fields['name'].initial = "New Relic Connection Info"
        self.fields["protocol"].required = True
        self.fields["port"].initial = 443
        self.fields["port"].required = True
        self.fields["ip"].required = True
        self.fields["ip"].initial = 'insights-api.newrelic.com'
        self.fields["use_auth_headers"].initial = True
        self.fields["use_auth_headers"].required = True
        self.fields['headers'].initial = {'license_key': None, 'query_key': None, 'new_relic_account_id': None}
        self.fields["headers"].help_text = mark_safe('You can get/create the keys from <a href="https://infrastructure.newrelic.com/accounts">infrastructure.newrelic.com/accounts</a>')
        self.fields["headers"].required = True

        # Remove connection info fields we do not need in new relic credentials
        del self.fields['ssh_key']
        del self.fields['username']
        del self.fields['password']

        # mark all fields as required
        for field in list(self.fields.values()):
            field.required = True

    def clean(self):
        new_relic_manager = NewRelicManager()
        ip = self.cleaned_data.get('ip')
        if not ip:
            raise forms.ValidationError("IP/Hostname is a required field")
        port = self.cleaned_data.get('port')
        if not port:
            raise forms.ValidationError("PORT is a required field")
        headers = self.cleaned_data.get('headers')
        if not headers:
            raise forms.ValidationError("Headers must be supplied.")

        ok, reason = new_relic_manager.verify_credentials(
            self.cleaned_data.get('protocol'),
            self.cleaned_data.get('ip'),
            self.cleaned_data.get('port'),
            self.cleaned_data.get('headers'),
        )
        if not ok:
            raise forms.ValidationError(
                f"{reason}")
        return self.cleaned_data
