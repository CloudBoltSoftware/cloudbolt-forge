from azure.storage.blob import BlockBlobService, PublicAccess


def generate_options_for_blob(**kwargs):
    file_names = []
    resource = kwargs.get('resource')
    if resource:
        azure_account_name = resource.azure_account_name
        block_blob_service = BlockBlobService(account_name=azure_account_name, account_key=resource.azure_account_key)

        blobs = block_blob_service.list_blobs(resource.azure_container_name)
        file_names.extend([blob.name for blob in blobs])

    return file_names


def run(resource, *args, **kwargs):
    container_name = resource.azure_container_name
    blob_name = "{{ blob }}"

    azure_account_name = resource.azure_account_name

    block_blob_service = BlockBlobService(account_name=azure_account_name, account_key=resource.azure_account_key)

    if block_blob_service.exists(container_name):
        try:
            block_blob_service.delete_blob(container_name, blob_name)
        except Exception as error:
            return "FAILURE", f"Failed to delete blob '{blob_name}'", f"{error}"
    else:
        return "FAILURE", f"Failed to delete Blob.'", f"Container don't exist."

    return "SUCCESS", f"Successfully deleted blob -> '{blob_name}'", ""
