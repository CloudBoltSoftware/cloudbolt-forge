"""
Deletes an Azure queue
"""
from azure.storage.queue import QueueService

from common.methods import set_progress


def run(job, **kwargs):
    resource = kwargs.pop("resources").first()

    queue_name = resource.attributes.get(field__name="azure_queue_name").value
    azure_storage_account_name = resource.attributes.get(
        field__name="azure_storage_account_name"
    ).value
    azure_account_key = resource.attributes.get(field__name="azure_account_key").value

    set_progress("Connecting To Azure...")
    queue_service = QueueService(
        account_name=azure_storage_account_name, account_key=azure_account_key
    )

    set_progress("Connection to Azure established")

    set_progress("Deleting queue %s..." % queue_name)
    queue_service.delete_queue(queue_name)

    return "Success", "The queue has been deleted", ""
