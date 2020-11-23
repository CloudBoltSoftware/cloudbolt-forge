from azure.storage.blob import BlockBlobService, PublicAccess
from servicecatalog.models import ServiceBlueprint
from resources.models import Resource, ResourceType
from accounts.models import Group


def run(resource, *args, **kwargs):
    azure_account_name = resource.azure_account_name

    block_blob_service = BlockBlobService(account_name=azure_account_name, account_key=resource.azure_account_key)

    blobs = block_blob_service.list_blobs(resource.azure_container_name)

    blueprint = ServiceBlueprint.objects.filter(name__icontains="blob").first()
    group = Group.objects.first()
    resource_type = blueprint.resource_type

    for blob in blobs:
        res, created = Resource.objects.get_or_create(
            name=blob.name,
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

    return "SUCCESS", "", ""
