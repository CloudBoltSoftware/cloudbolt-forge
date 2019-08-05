"""
Install a Custom Terraform Version for CloudBolt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Install a user-specified version of Terraform on CloudBolt.
This can be set as the Global Default in Admin Miscellaneous Settings.


Version Requirements
~~~~~~~~~~~~~~~~~~~~
CloudBolt 9.0
"""


import requests
import os
import hashlib
import zipfile
import tempfile
import shutil
import sys

from common.methods import set_progress
from django.conf import settings


TERRAFORM_DIR = settings.TERRAFORM_DIR
TERRAFORM_BIN_DIR = os.path.join(TERRAFORM_DIR, 'bin')


def run(job, *args, **kwargs):
    set_progress("Terraforming your CloudBolt...")

    # Initialize variables
    version_name = "{{ version_name }}"
    zip_url = "{{ zip_url }}"

    status, message, error = install_custom_terraform_binary(zip_url, version_name)

    return status, message, error


def install_custom_terraform_binary(zip_url: str, version_name: str):
    """
    Installs a version of Terraform from a custom ZIP URL and verifies it was installed correctly.
    Returns a Tuple:
        Status string
        Success message
        Error message
    """
    terraform_binary_base_directory = TERRAFORM_BIN_DIR

    response = None

    try:
        # Creates a temporary directory
        temp_dir = _create_temp_dir()
        if temp_dir is None:
            raise Exception('Failed to create a temp directory for the Terraform installation')
    
        # Download the ZIP to a temporary directory
        zip_file_path = _download_zip_file(zip_url, temp_dir.name)
        if zip_file_path is None:
            raise Exception(f'Failed to download the zip {zip_url} to {temp_dir.name}')
        if _is_zip_file(zip_file_path) is not True:
            raise Exception(f'The file provided at {zip_url} was not a Zip file!')
    
        # Unpacks the ZIP file
        if _unzip_file(zip_file_path, temp_dir.name) is not True:
            raise Exception(f'Failed to unzip {zip_file_path}')
    
        # Verifies a file named 'terraform' was unpacked
        terraform_binary_path = _get_terraform_binary_path(temp_dir.name)
        if terraform_binary_path is None:
            raise Exception(f'Failed to find a binary called `terraform` in the unpacked {zip_url}')
    
        # Verifies 'terraform' is a Linux binary
        if _is_linux_binary(terraform_binary_path) is not True:
            raise Exception(f'The provided binary was not a Liunx binary. Terraform Linux zip usually include `linux` in the name.')
    
        # Moves the `terraform` binary to /var/opt/cloudbolt/terraform/bin/terraform_version
        new_terraform_binary_path = os.path.join(terraform_binary_base_directory, f'terraform_{version_name}')
        if _move_terraform_version(terraform_binary_path, new_terraform_binary_path) is not True:
            raise Exception(f'Failed to copy terraform_{version_name} to {terraform_binary_base_directory}')
        if _set_terraform_binary_permissions(new_terraform_binary_path) is not True:
            raise Exception(f'Failed to set permissions on {new_terraform_binary_path}')

    except Exception as err:
        response = err.args[0]

    finally:
        # Cleans up temporary files
        cleanup_status = _cleanup_temp_dir(temp_dir)
        if cleanup_status is not True:
            response = ('WARNING', '', f'Failed to clean up temporary files on disk in {temp_dir.name}')

    if response is None:
        return 'SUCCESS', f'Successfully instaled Terraform! Go to Miscellaneous Settings to set terraform_{version_name} as the CloudBolt global default.', ''
    else:
        return 'FAILURE', '', response


def _create_temp_dir():
    """
    Returns a Temporary Directory.
    If that fails, it returns None
    """
    try:
        return tempfile.TemporaryDirectory()
    except:
        return None


def _download_zip_file(zip_url, temp_dir):
    """
    Downloads a given zip URL into the desired temp directory.
    """
    with requests.get(zip_url, stream=True) as request:
        zip_fname = zip_url.split('/')[-1]
        zip_file_path = os.path.join(temp_dir, zip_fname)
        with open(zip_file_path, 'wb') as zip_file:
            zip_file.write(request.content)
    
    if os.path.isfile(zip_file_path):
        return zip_file_path
    else:
        return None


def _is_zip_file(zip_file_path):
    """
    Return True or False if a given path is a Zip file
    """
    return zipfile.is_zipfile(zip_file_path)


def _unzip_file(zip_file_path, temp_dir):
    """
    Unzips a zip_file to the given temp_dir.
    Returns True if successful, False if unsuccessful.
    """
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    return True


def _get_terraform_binary_path(temp_dir):
    """
    Returns the path to the `terraform` binary in the given temp_dir.
    Returns None otherwise.
    """
    terraform_location = os.path.join(temp_dir, 'terraform')
    if os.path.isfile(terraform_location):
        return terraform_location
    else:
        return None


def _is_linux_binary(fpath):
    """
    Reads a magic byte and determines if the file given is a Linux (ELF) binary.
    """
    with open(fpath, 'rb') as f:
        return f.read(4) == b'\x7fELF'


def _move_terraform_version(temp_terraform_binary_location, new_terraform_binary_location):
    """
    Moves the `terraform` file in the temp directory to
        /var/opt/cloudbolt/terraform/bin/terraform_{version}
    return True if successful
    return False if not successful
    """
    try:
        shutil.move(temp_terraform_binary_location, new_terraform_binary_location)
        return True
    except FileNotFoundError as e:
        set_progress(e)
        return False


def _set_terraform_binary_permissions(binary_path):
    """
    Sets the new terraform binary to be executable.
    """
    try:
        os.chmod(binary_path, 0o755)
        try:
            shutil.chown(binary_path, user='apache', group='apache')
        except:
            set_progress(f'Unable to set permissions to apache:apache on {binary_path}. This may cause problems!')
            pass
        return True
    except OSError:
        return False


def _cleanup_temp_dir(temp_dir):
    """
    Runs cleanup on a TemporaryDirectory
    If successful it returns True
    If that fails it returns None
    """
    try:
        temp_dir.cleanup()
        return True
    except:
        return None
