from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from botocore.client import ClientError
import boto3


def run(resource, **kwargs):
    SkipFinalSnapshot = "{{ SkipFinalSnapshot }}"
    FinalDBSnapshotIdentifier = "{{ FinalDBSnapshotIdentifier }}"

    region = resource.aws_region
    rh_id = resource.aws_rh_id

    db_cluster_identifier = resource.name

    handler = AWSHandler.objects.get(id=rh_id)
    set_progress('Connecting to Amazon RDS')
    try:
        wrapper = handler.get_api_wrapper()
    except Exception:
        return
    
    client = wrapper.get_boto3_client(
        'docdb',
        handler.serviceaccount,
        handler.servicepasswd,
        region
    )
    set_progress('Deleting cluster "{}"'.format(db_cluster_identifier))

    try:
        if SkipFinalSnapshot:
            client.delete_db_cluster(
                DBClusterIdentifier=db_cluster_identifier,
                SkipFinalSnapshot=SkipFinalSnapshot,
                FinalDBSnapshotIdentifier=FinalDBSnapshotIdentifier
            )
        else:
            client.delete_db_cluster(
                DBClusterIdentifier=db_cluster_identifier,
                SkipFinalSnapshot=True)

            # wait for the deletion to complete before returning
            try:
                client.describe_db_clusters(DBClusterIdentifier=db_cluster_identifier)
            except Exception:
                # database has been successfully deleted
                return "SUCCESS", "Cluster has successfully been deleted", ""

    except ClientError as e:
        set_progress(f'AWS ClientError: {e}')
        return "FAILURE", "FAILED", f"{e}"
