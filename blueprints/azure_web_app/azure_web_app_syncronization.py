"""
This plugin is to synchronize Azure Web App resources

It should be placed in Orchestration Actions at the
Post Sync VMs Hookpoint.

Additionally, this action should have its Resource Technology limited to Azure

"""
if __name__ == "__main__":
    import os
    import sys
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    sys.path.append("/opt/cloudbolt")
    django.setup()

from common.methods import set_progress
from infrastructure.models import CustomField
from jobs.models import Job
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.web import WebSiteManagementClient

from resources.models import ResourceType, Resource
from servicecatalog.models import ServiceBlueprint
from accounts.models import Group

from utilities.logger import ThreadLogger


logger = ThreadLogger(__name__)


def _get_clients(handler):
    """
    Get the clients using newer methods from the CloudBolt main repo if this CB is running
    a version greater than 9.2. These internal methods implicitly take care of much of the other
    features in CloudBolt such as proxy and ssl verification.
    Otherwise, manually instantiate clients without support for those other CloudBolt settings.
    :param handler:
    :return:
    """
    import settings
    from common.methods import is_version_newer

    set_progress("Connecting To Azure...")

    cb_version = settings.VERSION_INFO["VERSION"]
    if is_version_newer(cb_version, "9.2"):
        from resourcehandlers.azure_arm.azure_wrapper import configure_arm_client

        wrapper = handler.get_api_wrapper()
        web_client = configure_arm_client(wrapper, WebSiteManagementClient)
        resource_client = wrapper.resource_client
    else:
        # TODO: Remove once versions <= 9.2 are no longer supported.
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id,
            secret=handler.secret,
            tenant=handler.tenant_id,
        )
        web_client = WebSiteManagementClient(credentials, handler.serviceaccount)
        resource_client = ResourceManagementClient(credentials, handler.serviceaccount)

    set_progress("Connection to Azure established")

    return web_client, resource_client


def run(job, **kwargs):
    # Connect to Azure Management Service
    azure = AzureARMHandler.objects.first()
    web_client, resource_client = _get_clients(azure)

    # Generate custom fields
    CustomField.objects.get_or_create(
        name="web_app_id",
        label="Azure Web App ID",
        type="STR",
        description="Used by the Azure Web App resource & blueprint.",
    )

    # Generate custom fields
    CustomField.objects.get_or_create(
        name="web_app_location",
        label="Azure Web App Location",
        type="STR",
        description="Used by the Azure Web App resource & blueprint.",
    )

    # Generate custom fields
    CustomField.objects.get_or_create(
        name="web_app_default_host_name",
        label="Azure Web App Host Name",
        type="URL",
        description="Used by the Azure Web App resource & blueprint.",
    )

    # Generate custom fields
    # CustomField.objects.get_or_create(
    #    name='resource_group_name', label='Azure Web App Host Name', type='STR',
    #    description='Resource Group Name.'
    # )

    # Get the 'Azure Web App' blueprint
    bp = ServiceBlueprint.objects.get(id=6)

    # Just use a specific group for now
    group = Group.objects.get(id=2)

    # Make Discovered Azure Web Apps CloudBolt Resource Types. 'Web Apps'
    rt = ResourceType.objects.get(name="web_apps")

    # Get existing (Active) Web Apps Resources from CloudBolt
    cb_web_apps = Resource.objects.filter(
        resource_type__name="web_apps", lifecycle="ACTIVE"
    )
    cb_app_ids = []
    for app in cb_web_apps:
        cb_app_ids.append(app.web_app_id)

    # Discover Resource Groups with Web Apps
    set_progress("Getting List of Web Apps by Resource Groups")

    for groups in resource_client.resource_groups.list():
        web_apps = web_client.web_apps.list_by_resource_group(
            resource_group_name=groups.name
        )
        web_app_ids = []
        for web_app in web_apps:
            # Skip creation if Web App already exists
            if web_app.id in cb_app_ids:
                set_progress(
                    "Web App: '{}' already exists in CloudBolt. Skipping...".format(
                        web_app.name
                    )
                )
                web_app_ids.append(web_app.id)
                continue
            # Create the Resource in CloudBolt
            set_progress("Creating Resource in CloudBolt for {}".format(web_app.name))
            r = Resource(
                name=web_app.name,
                resource_type=rt,
                lifecycle="ACTIVE",
                blueprint=bp,
                group=group,
            )
            r.save()
            # Store Web App metadata on the resource as parameters for teardown
            r.set_value_for_custom_field(cf_name="web_app_id", value=web_app.id)
            r.set_value_for_custom_field(
                cf_name="web_app_location", value=web_app.location
            )
            r.set_value_for_custom_field(
                cf_name="web_app_default_host_name", value=web_app.default_host_name
            )
            r.set_value_for_custom_field(
                cf_name="resource_group_name", value=web_app.resource_group
            )

            web_app_ids.append(web_app.id)

        # Remove Web Apps that no longer exist
        cb_apps_in_group = []
        for app in cb_web_apps:
            if app.resource_group_name == groups.name:
                cb_apps_in_group.append(app)
        for app in cb_apps_in_group:
            if app.web_app_id not in web_app_ids:
                set_progress(
                    "Web App: '{}' no longer exists. Removing from CloudBolt...".format(
                        app
                    )
                )
                delete = app.available_actions()[0]["action"]
                delete.run_hook_as_job(resources=[app])


if __name__ == "__main__":
    job_id = sys.argv[1]
    job = Job.objects.get(id=job_id)
    run = run(job)
