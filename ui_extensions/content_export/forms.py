import datetime
from django import forms

from common.forms import C2Form

VERSION_CHOICES = [('8.6', '8.6'), ('8.7', '8.7'), ('8.8', '8.8'), ('9.0', '9.0')]


class ExportContentForm(C2Form):

    display_name = forms.CharField(label="Instance", required=False)
    mvr = forms.ChoiceField(label="Min. Version Req.", choices=VERSION_CHOICES, required=False)
    last_updated = forms.CharField(label="Last Updated", required=False)

    def __init__(self, *args, **kwargs):
        self.initial_instance = kwargs.pop('instance')
        super(ExportContentForm, self).__init__(*args, **kwargs)
        if self.initial_instance:
            basic_data = self.initial_instance.basic_exportable_metadata()

            self.fields["display_name"].initial = basic_data['display_name']
            self.fields["mvr"].initial = basic_data["minimum_version_required"]
            self.fields["list_image"] = self.initial_instance._meta.get_field(
                "library_list_image").formfield()
            self.fields["list_image"].initial=self.initial_instance.library_list_image
            last_updated_initial = datetime.date.today()
            if basic_data['last_updated'] != '':
                last_updated_initial = self.initial_instance.last_updated
            updated_field = self.fields["last_updated"]
            updated_field.widget = forms.TextInput(attrs={'class': 'render_as_datepicker'})
            updated_field.initial = last_updated_initial

    def save(self):
        from common.methods import mkDateTime
        instance = self.initial_instance
        display_name = self.cleaned_data['display_name']
        if display_name and hasattr(instance, 'label'):
            instance.label = display_name
        instance.minimum_version_required = self.cleaned_data['mvr']
        updated = self.cleaned_data['last_updated']
        if updated:
            instance.last_updated = mkDateTime(updated)
        else:
            instance.last_updated = None
        instance.library_list_image = self.cleaned_data['list_image']
        instance.save()
        return instance
