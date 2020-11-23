from common.methods import set_progress
from azure.storage.blob import BlockBlobService, PublicAccess
import os


def generate_options_for_file_name(**kwargs):
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
    file_name = "{{ file_name }}"
    download_to = "{{ download_to }}"

    azure_account_name = resource.azure_account_name

    block_blob_service = BlockBlobService(account_name=azure_account_name, account_key=resource.azure_account_key)

    path = os.path.expanduser(download_to)

    file = file_name
    full_path_to_file = os.path.join(path, file)

    file_exists = os.path.isfile(full_path_to_file)
    set_progress(f"Downloading '{file}' from Blob storage...")

    try:
        block_blob_service.get_blob_to_path(container_name, file, full_path_to_file)
    except Exception as e:
        if not file_exists:
            os.remove(full_path_to_file)
        return "FAILURE", f"Failed to download `{file}`.", f"{e}"
    return "SUCCESS", f"Downloaded `{file}` successfully.", ""
