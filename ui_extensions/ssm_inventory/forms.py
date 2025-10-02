from django import forms
from common.forms import C2Form
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

class PatchEC2Form(C2Form):
    def __init__(self, *args, **kwargs):
        super(PatchEC2Form, self).__init__(*args, **kwargs)
        initial = kwargs.get("initial", {})
        self.fields["operation"] = forms.ChoiceField(
            label="Operation",
            choices=[("Install", "Install"), ("Scan", "Scan")],
            required=True,
            initial=initial.get("operation", None),
            help_text="Choose to either install missing patches or scan",
            widget=forms.Select()
        )
        self.fields["reboot_option"] = forms.ChoiceField(
            label="Reboot Operation",
            choices=[
                ("RebootIfNeeded", "Reboot if Needed"),
                ("NoReboot", "No Reboot")
            ],
            required=True,
            initial=initial.get("reboot_option", None),
            help_text="Should the server be rebooted if needed",
            widget=forms.Select()
        )

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self):
        operation = self.cleaned_data.get("operation")
        reboot_option = self.cleaned_data.get("reboot_option")
        return operation, reboot_option
