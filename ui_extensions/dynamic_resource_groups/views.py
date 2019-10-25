from accounts.models import Group
from extensions.views import tab_extension, TabExtensionDelegate
from infrastructure.models import CustomField


class DynamicResourceGroupTabDelegate(TabExtensionDelegate):
    def should_display(self):
        # Should we check @permissions.cb_permission_required("group.manage_parameters")
        # here?
        _ = create_tags_to_include_custom_field()

        return True


def create_tags_to_include_custom_field():
    """
    Automatically create "Tags to Include" CF on XUI rendering.
    """
    rule_custom_field, _ = CustomField.objects.get_or_create(name="tags_to_include")
    rule_custom_field.label = "Tags to Include"
    rule_custom_field.type = "CODE"
    rule_custom_field.save()
    return

@tab_extension(model=Group, title="Policies", delegate=DynamicResourceGroupTabDelegate)
def group_dynamic_policies_tab(request, obj_id):
    pass
