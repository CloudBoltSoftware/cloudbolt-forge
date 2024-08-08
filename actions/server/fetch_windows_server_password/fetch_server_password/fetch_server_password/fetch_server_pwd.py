import base64
import rsa

from resourcehandlers.aws.models import AWSHandler
from resourcehandlers.awsjit.models import AWSJITHandler
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


def _decrypt_ciphertext(cipher: bytes, private_key: str) -> str:
    pkey = rsa.PrivateKey.load_pkcs1(private_key)
    value = rsa.decrypt(cipher, pkey)

    return value.decode("utf-8")


def _get_password_data_from_ec2_instance(server) -> str:
    rh = server.resource_handler.cast()
    env = server.environment
    ec2_client = rh.get_boto3_resource(env.aws_region, "ec2")
    instance = ec2_client.Instance(server.resource_handler_svr_id)

    return instance.password_data().get("PasswordData")


def run(server, **kwargs):
    """
    This plugin will return the generated adminstrator password for a given Windows
    EC2 VM. In most cases, permissions to execute this Server Action should be granted
    to the Server Owner and Delegated Server Owners.
    """
    rh = server.environment.resource_handler.cast()

    # Ensure the resource handler is AWS-based
    if type(rh) not in [AWSHandler, AWSJITHandler]:
        return (
            "FAILURE",
            "",
            "This Server Action should only be run against AWS EC2 instances.",
        )

    # Ensure this is a Windows server and it has a key pair name
    if not (server.os_family.name == "Windows" and server.key_name):
        return (
            "FAILURE",
            "",
            f"Server {server.hostname} must be running Windows and have its key name "
            f"set. This private key material should be stored in CloudBolt and "
            f"available to the server's resource handler.",
        )

    try:
        pwd_data = _get_password_data_from_ec2_instance(server)
        key = rh.sshkey_set.get(name=server.key_name).cast()
        ciphertext = base64.b64decode(pwd_data)
        password = _decrypt_ciphertext(ciphertext, key.private_key)
    except Exception as ex:
        logger.error(f"Unable to decrypt server password: {ex}")
        return "FAILURE", "", ""

    return "SUCCESS", password, ""


def should_display(server, request=None):
    """
    A conditional display plugin to determine whether or not this action should be
    displayed.
    """
    rh = server.environment.resource_handler.cast()
    return (
        type(rh) in [AWSJITHandler, AWSHandler]
        and server.os_family.name == "Windows"
        and server.key_name
    )
