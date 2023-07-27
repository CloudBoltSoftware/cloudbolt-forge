"""
This plugin will get or create a blueprint with the specified Global ID. The
Remote Source URL passed in will be updated for the blueprint and the BP will
be refreshed from the Remote Source.

To use:
1. Create an Inbound Webhook (Admin > Inbound Webhooks) using the code below.
2. Configure the webhook to use either token based authentication or Default CB
   API authentication.
3. Send a REST request using the selected authentication. The following
   are valid parameters

Parameters:
    blueprint_id: The Global ID of the Blueprint to update - this should be the
        Global ID of the Blueprint in CloudBolt (ex. BP-abcd1234)
    remote_source_url: The URL of the new Remote Source to use for the Blueprint
    remote_source_password: An API token for the remote source, if required
"""
from common.methods import set_progress
from servicecatalog.models import ServiceBlueprint


def inbound_web_hook_post(*args, parameters={}, **kwargs):
    set_progress(
        f"This message will show up in CloudBolt's application.log. args: "
        f"{args}, kwargs: {kwargs}, parameters: {parameters}"
    )
    blueprint_id = parameters.get("blueprint_id", None)
    remote_source_url = parameters.get("remote_source_url", None)
    remote_source_password = parameters.get("remote_source_password", None)
    if not blueprint_id:
        raise ValueError("Blueprint ID is required")
    if not remote_source_url:
        raise ValueError("Remote Source URL is required")
    bp, created = ServiceBlueprint.objects.get_or_create(global_id=blueprint_id)
    if created:
        set_progress(f"Created new Blueprint with Global ID: {blueprint_id}")
    else:
        set_progress(f"Found existing Blueprint with Global ID: {blueprint_id}")
    set_progress(f"Updating Blueprint with Remote Source URL: "
                 f"{remote_source_url}")
    bp.remote_source_url = remote_source_url
    if remote_source_password:
        bp.remote_source_password = remote_source_password
    bp.save()
    bp.refresh_from_remote_source()

    return (
        {
            "message": "Successfully updated the Blueprint Remote Source",
            "result": f"Blueprint ID: {blueprint_id} updated to use Remote "
                      f"Source URL: {remote_source_url}",
        }
    )
