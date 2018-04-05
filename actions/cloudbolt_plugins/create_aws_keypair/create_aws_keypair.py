"""
A hook that creates a key pair on the EC2 region of the environment, adds it
to the list of available keypairs on that environment, and injects the newly
generated keypair as the one to provision the server with.

Usage Instructions
    1. Turn off required for key_pair at the console:
        cf = CustomField.objects.get(name="key_name")
        cf.required = False
        cf.save()

    2. Add two new Parameters in the Admin section of the site:

        * Label: Name of Key Pair to Create
          Name: name_of_key_pair_to_create
          Description: Enter a unique name for a key pair to be generated at
                       server provision time.
          Type: String
          Show on servers: Checked

        * Label: Private Key
          Name: private_key
          Description: The private key generated for this server when it was
                       provisioned by CloudBolt. (Created with the hook
                       "create_keypair.py".)
          Type: Multi-line Text
          Show on servers: Checked

    3. Add the "Name of Key Pair to Create" Parameter to your AWS Environment.

    4. Enable this plug-in at the "Pre-Create Resource" trigger point
"""
import os

from infrastructure.models import CustomField
from orders.models import CustomFieldValue
import settings

# if set to true, save the new key on the filesystem
SAVE_KEY_ON_FILESYSTEM = True


def run(job, logger=None):
    debug("Running hook {}. job.id={}".format(__name__, job.id), logger, job)
    server = job.server_set.first()
    key_name = server.name_of_key_pair_to_create

    if server.resource_handler.type_slug != "aws":
        return ("", "", "")

    if key_name is None:
        return ("", "", "")

    if server.key_name is not None:
        msg = (
            "New keypair name '{}' to create was entered "
            "but existing key '{}' was also selected."
        ).format(key_name, server.key_name)
        debug(msg, logger, job)
        return ("FAILURE", "", msg)

    e = server.environment
    debug("Connecting to EC2 region {}.".format(e.aws_region), logger, job)
    rh = server.resource_handler
    aws = rh.cast()
    aws.connect_ec2(e.aws_region)
    ec2 = aws.resource_technology.work_class.ec2

    key_name_cf = CustomField.objects.get(name="key_name")
    key_name_cfv = CustomFieldValue.objects.create(field=key_name_cf,
                                                   value=key_name)

    if key_name in [kp.name for kp in ec2.get_all_key_pairs()]:
        debug(
            "Keypair with name '{}' already exists in {}, using it.".format(
                key_name,
                e.aws_region
            ),
            logger,
            job
        )
        # delete existing cfv and replace it with the one for this keypair
        server.custom_field_values.add(key_name_cfv)

        return ("", "", "")

    debug(
        "Creating keypair named '{}' in {}.".format(key_name, e.aws_region),
        logger,
        job
    )
    key_pair = ec2.create_key_pair(key_name)

    debug("Recording private key on server parameter.", logger, job)
    server.private_key = key_pair.material

    debug("Injecting key name into server for provisioning.", logger, job)
    # Note: The key doesn't need to appear in the options list for key pair!
    server.key_name = key_name

    debug("Remembering key for future use with this Environment.", logger, job)
    # Add the key to the options for the AWS Parameter "Key pair name"
    # Notes: If you want to do some tests against existing field options:
    #    cfo = list(e.custom_field_options.all())
    e.custom_field_options.add(key_name_cfv)

    if SAVE_KEY_ON_FILESYSTEM:
        save_key_on_cb_server(key_name, key_pair.material, server)

    return ("", "", "")


def save_key_on_cb_server(key_name, key_value, server):
    """
    Save the key to a new keyfile in the file system and set the file
    permissions for later use.
    """
    key_path = os.path.join(
        settings.VARDIR, "opt", "cloudbolt", "resourcehandlers",
        server.resource_handler.type_slug,
        str(server.resource_handler_id),
        "{}.pem".format(key_name))
    with open(key_path, 'w') as key_file:
        key_file.write(key_value)
        key_file.seek(0)
        os.chmod(key_path, 0600)


def debug(message, logger, job):
    job.set_progress(message)
    if logger:
        logger.debug(message)
    else:
        print(message)
