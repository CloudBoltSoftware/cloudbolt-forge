from common.methods import set_progress
from azure.storage.blob import BlockBlobService, PublicAccess
import os
from servicecatalog.models import ServiceBlueprint
from resources.models import Resource, ResourceType
from accounts.models import Group


def generate_options_for_file_name(control_value=None, **kwargs):
    names = []
    if control_value:
        path = os.path.expanduser(control_value)
        names.extend([x for x in os.listdir(path)])
    return names


def run(resource, *args, **kwargs):
    container_name = resource.azure_container_name
    file_name = "{{ file_name }}"
    path = "{{ path }}"

    azure_account_name = resource.azure_account_name

    block_blob_service = BlockBlobService(account_name=azure_account_name, account_key=resource.azure_account_key)

    full_path_to_file = os.path.join(path, file_name)

    set_progress(f"Uploading '{file_name}' to Blob storage...")
    error = block_blob_service.create_blob_from_path(container_name, file_name, full_path_to_file)
    if error:
        return "FAILURE", f"Failed to upload '{file_name}'", f"{error}"
    else:
        blueprint = ServiceBlueprint.objects.filter(name__iexact="Azure blob").first()

        resource_type = blueprint.resource_type
        group = Group.objects.first()

        res, created = Resource.objects.get_or_create(
            name=file_name,
            defaults={
                'blueprint': blueprint,
                'group': group,
                'parent_resource': resource,
                'resource_type': resource_type})
        if not created:
            res.blueprint = blueprint
            res.group = group
            res.parent_resource = resource
            res.resource_type = resource_type

            res.save()
        return "SUCCESS", f"Uploaded '{file_name}' Successfully.", ""
