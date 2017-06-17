"""
This action supplies choices for several Azure-related parameters, so that
end users see dropdowns for these action inputs rather than just text fields.
"""
from infrastructure.models import Environment


def get_options_list(field, profile=None, **kwargs):
    if field.name == 'azure_service_tier':
        return azure_service_tier_choices()
    if field.name == 'azure_performance_level':
        return azure_performance_level_choices()
    if field.name == 'azure_environment':
        return azure_arm_environment_choices(profile)
    return []


def azure_service_tier_choices():
    """
    Service tier (aka 'edition') is an optional 
    """
    return [
        ('Basic', 'Basic'),
        ('Standard', 'Standard'),
        ('Premium', 'Premium'),
    ]


def azure_performance_level_choices():
    """
    Service Level is a required parameter for new SQL Database.

    This list was returned by a call to `list_service_level_objectives` with
    a server in West US.
    http://azure-sdk-for-python.readthedocs.io/en/latest/ref/azure.servicemanagement.sqldatabasemanagementservice.html#azure.servicemanagement.sqldatabasemanagementservice.SqlDatabaseManagementService.list_service_level_objectives
    """
    return [
        (u'dd6d99bb-f193-4ec1-86f2-43d3bccbc49c', u'Basic'),
        (u'f1173c43-91bd-4aaa-973c-54e79e15235b', u'S0'),
        (u'1b1ebd4d-d903-4baa-97f9-4ea675f5e928', u'S1'),
        (u'455330e1-00cd-488b-b5fa-177c226f28b7', u'S2'),
        (u'789681b8-ca10-4eb0-bdf2-e0b050601b40', u'S3'),
        (u'66add646-e451-4d66-8589-680c60a920cc', u'S4'),
        (u'7203483a-c4fb-4304-9e9f-17c71c904f5d', u'P1'),
        (u'a7d1b92d-c987-4375-b54d-2b1d0e0f5bb0', u'P2'),
        (u'a7c4c615-cfb1-464b-b252-925be0a19446', u'P3'),
        (u'43940481-9191-475a-9dba-6b505615b9aa', u'P6'),
        (u'26e021db-f1f9-4c98-84c6-92af8ef433d7', u'System'),
        (u'a45fea0c-e63c-4bf0-9f81-9964c86b7d2a', u'System Standard'),
        (u'910b4fcb-8a29-4c3e-958f-f7ba794388b2', u'Shared')
    ]



def azure_arm_environment_choices(profile):
    """
    Return a list of choices like [(env-id, env-name), ...] for all Azure ARM
    environments this user has permission to see.
    """
    envs_this_user_can_view = Environment.objects_for_profile(profile)
    arm_handlers = AzureARMHandler.objects.all()
    arm_envs = envs_this_user_can_view.filter(resource_handler_id__in=arm_handlers)
    return [(env.id, env.name) for env in arm_envs]
