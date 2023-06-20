from azure.storage.blob import BlockBlobService


def run(resource, *args, **kwargs):
    container_name = resource.azure_container_name

    azure_account_name = resource.azure_account_name

    block_blob_service = BlockBlobService(account_name=azure_account_name, account_key=resource.azure_account_key)

    if block_blob_service.exists(container_name):
        try:
            block_blob_service.delete_container(container_name)
        except Exception as error:
            return "FAILURE", f"Failed to delete container '{container_name}'", f"{error}"
    else:
        return "FAILURE", f"Failed to delete container '{container_name}'", f"Container don't exist."

    return "SUCCESS", f"Successfully deleted container -> '{container_name}'", ""
