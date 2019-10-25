from common.forms import EditParameterValueForm
from orders.models import CustomFieldValue


class EditDynamicGroupRuleForm(EditParameterValueForm):
    """
    [summary]
    """

    associated_obj_type = "group"
    run_param_change_job = False

    def save(self):
        group = self.obj
        _ = group.custom_field_options.filter(
            field__namespace__name="Dynamic Group Rules"
        ).delete()

        value = self.cleaned_data["value"]
        cfv = CustomFieldValue.objects.create(field=self.field, value=value)
        group.custom_field_options.add(cfv)
        group.save()
        return
