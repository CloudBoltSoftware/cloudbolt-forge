from django import forms
from django.utils.translation import ugettext as _, ugettext_lazy as _lazy

from common.forms import C2Form
from infrastructure.models import CustomField, Namespace, Server
from utilities.logger import ThreadLogger

from common.widgets import SelectizeSelect

logger = ThreadLogger(__name__)


class ClientForm(C2Form):
    server_id=forms.CharField(widget=forms.widgets.HiddenInput())
    dns_name_or_ip=forms.CharField(max_length=256,
    required=True)
    user_name=forms.CharField(max_length=256,
    required=True)
    password=forms.CharField(widget=forms.PasswordInput())

    def save(self, profile):
        server_id = self.cleaned_data['server_id']
        host = self.cleaned_data['host']
        user_name = self.cleaned_data['user_name']
        password = self.cleaned_data['password']
        server = Server.objects.get(id=server_id)

        msg = _("Added a new client to '{server}'")

        return True, msg.format(server=server.hostname)
