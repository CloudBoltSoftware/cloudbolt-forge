"""
Install Terraform on CloudBolt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Install a user-specified version of Terraform on CloudBolt.


Version Requirements:
~~~~~~~~~~~~
CloudBolt 9.0
"""


import urllib
import os
import hashlib
import zipfile

from common.methods import set_progress
from django.conf import settings


HASHICORP_TERRAFORM_DOWNLOAD_FORMAT_URL=(
    'https://releases.hashicorp.com/terraform/{version}/terraform_{version}_linux_amd64.zip'
)
HASHICORP_TERRAFORM_SHA_256_SUM_FORMAT_URL=(
    'https://releases.hashicorp.com/terraform/{version}/terraform_{version}_SHA256SUMS'
)

TERRAFORM_DIR=settings.TERRAFORM_DIR
TERRAFORM_BIN_DIR=os.path.join(TERRAFORM_DIR, 'bin')
TERRAFORM_BINARY=os.path.join(TERRAFORM_BIN_DIR, 'terraform')


def run(job, *args, **kwargs):
    set_progress("Terraforming your CloudBolt...")

    # Initialize variables
    version = set_version(
        '''{{ version }}'''
    )
    custom_file_url = set_custom_file_url(
       '''{{ custom_file_url }}'''
    )
    sha_256_sum = set_sha_256_sum(
        '''{{ sha_256_sum }}'''
    )
    existing_version = set_existing_version(
        '''{{ existing_version }}'''
    )
    make_default = set_make_default(
        '''{{ set_as_default }}'''
    )
    overwrite_existing = set_overwrite_existing(
        '''{{ overwrite_existing }}'''
    )

    # The decision tree is as follows:
    # If selected, we use the existing_version input.
    # If provided, we use the custom URL.
    # Last we use the version provided.
    if existing_version != '':
        status, new_path, err = install_existing_version(existing_version)
        version = existing_version
    elif custom_file_url != '' and version != '':
        status, new_path, err = install_custom_file_url(custom_file_url, sha_256_sum, version, overwrite_existing)
    elif version != '':
        status, new_path, err = install_version(version, overwrite_existing)
    else:
        return 'FAILURE', '', 'Not enough parameters given. You must provide a Terraform version, URL and version, or an existing version!'

    if not status == "SUCCESS":
        return status, '', "Failed to install the desired version of Terraform: {reason}".format(reason=err)

    if make_default == True:
        make_bin_default(new_path, default_fname=TERRAFORM_BINARY)

    return 'SUCCESS', 'Successfully configured Terraform v{version}'.format(version=version), ''


def set_version(version: str):
    return str(version)


def set_custom_file_url(custom_file_url: str):
    return str(custom_file_url)


def set_sha_256_sum(sha_256_sum: str):
    return str(sha_256_sum)


def set_existing_version(existing_version: str):
    return str(existing_version)


def generate_options_for_existing_version(**kwargs):
    options = []
    terraform_bin_files = os.listdir(TERRAFORM_BIN_DIR)
    for tf in terraform_bin_files:
        if tf == 'terraform':
            continue
        options.append(tf)
    return options


def set_make_default(make_default: str):
    return bool(make_default)


def set_overwrite_existing(overwrite_existing: str):
    if overwrite_existing == 'True':
        return True
    else:
        return False


def install_existing_version(version: str):
    set_progress('Using existing Terraform version {version}'.format(version=version))
    version_fname = os.path.join(TERRAFORM_BIN_DIR, version)
    if file_already_exists(version_fname):
        return 'SUCCESS', version_fname, ''
    else:
        return 'FAILURE', '', 'Could not find terraform binary at {version_fname}'.format(version_fname=version_fname)


def install_custom_file_url(custom_url: str, sha_256_sum: str, version: str, overwrite_existing: bool, zipped: bool = False):
    """
    Installs a version of Terraform from a custom URL and verifies it was installed correctly.
    Processes the downloaded artifact differently if it was a ZIP file or just a raw binary.
    """
    base_dir   = TERRAFORM_BIN_DIR
    dl_fname   = os.path.join(base_dir, 'terraform_{version}.download'.format(version=version))
    dest_fname = os.path.join(base_dir, 'terraform_{version}'.format(base_dir=base_dir, version=version))

    set_progress('Installing Terraform from {custom_url} with verification SHA {sha_256_sum} to location {dest_fname}'.format(custom_url=custom_url, sha_256_sum=sha_256_sum, dest_fname=dest_fname))

    # Overwrite existing short-circuit check
    version_exists = file_already_exists(dest_fname)
    set_progress(f'Verfiying if we should overwrite this file {dest_fname} {version_exists} {overwrite_existing}')
    if version_exists == True and overwrite_existing == False:
        return 'WARNING', '', 'Skipped installation. The download would overwrite an existing Terraform binary at {dest_fname}'.format(dest_fname=dest_fname)

    set_progress('Guarenteeing directories)')
    # Make sure the directory we are downloading to exists
    if not os.path.exists(os.path.dirname(dl_fname)):
        os.makedirs(os.path.dirname(dl_fname))

    set_progress('making urllib request')
    # Fetch the custom URL contents
    _, _= urllib.request.urlretrieve(custom_url, dl_fname)
    
    if not os.path.isfile(dl_fname):
        return 'FAILURE', '', 'Failed to download anything from {custom_url}'.format(custom_url)

    set_progress('SHA verification')
    # SHA VERIFY
    if not sha_256_verify(dl_fname, sha_256_sum):
        return 'FAILURE', '', 'Downloaded artifact did not match the expected SHA checksum'

    if zipped == True:
        set_progress('Zipped file processing')
        unzipped_fname = os.path.join(os.path.dirname(dl_fname), 'terraform')
        # We have to remove the existing `terraform` symlink first before the unzip
        try:
            os.remove(unzipped_fname)
        except FileNotFoundError:
            pass
        # This is a zip file, so we have to open and unzip it
        with zipfile.ZipFile(dl_fname, "r") as zip_ref:
            # We unzip into the same directory we downloaded to
            zip_ref.extractall(os.path.dirname(dl_fname))
        # move os.path.join(os.path.dirname(dl_fname), 'terraform') to os.path.join(os.path.dirname(dl_fname), 'terraform_{version}')
        set_progress(f'Renaming {unzipped_fname} -> {dest_fname}')
        os.rename(unzipped_fname, dest_fname)
        os.remove(dl_fname)
    elif is_linux_binary(dl_fname):
        set_progress('Binary file processing')
        # move os.path.join(dl_fname) to os.path.join(os.path.dirname(dl_fname), 'terraform_{version}')
        set_progress(f'Renaming {dl_fname} -> {dest_fname}')
        os.rename(dl_fname, dest_fname)
    else:
        os.remove(dl_fname)
        return 'FAILURE', '', 'Given URL must provide a Linux binary!'

    set_progress('Setting execute bit')
    os.chmod(dest_fname, 0o744)

    return 'SUCCESS', dest_fname, ''


def install_version(version: str, overwrite_existing: bool):
    """
    Given a version number for Terraform, installs that version via install_custom_file_url
    """
    set_progress('Installing Terraform v{version} from Hashicorp.'.format(version=version))

    bin_url = HASHICORP_TERRAFORM_DOWNLOAD_FORMAT_URL.format(version=version)
    sha_256_sum = get_terraform_sha(version)

    if sha_256_sum is None:
        return 'FAILURE', '', 'Could not find SHA 256 SUM for Terraform {version}'.format(version=version)

    status, path, err = install_custom_file_url(bin_url, sha_256_sum, version, overwrite_existing, zipped=True)

    return status, path, err


def get_terraform_sha(version: str):
    """
    Gets the expected SHA 256 sum for a given version of Terraform.
    """
    sha_url = HASHICORP_TERRAFORM_SHA_256_SUM_FORMAT_URL.format(version=version)

    # Make an HTTP query to get the expected SHA 256 SUM for this version of Terraform
    sha_256_sum_text = ''
    with urllib.request.urlopen(sha_url) as sha_response:
        # Parse the repsonse into a text block
        sha_256_sum_text = sha_response.read().decode('utf-8')

    # The line is a bunch of SHA256SUMs like this:
    # 817be651ca...d5cfd31  terraform_0.11.4_linux_amd64.zip
    for line in sha_256_sum_text.split('\n'):
        split_line = line.split('  ')
        if split_line[1] == 'terraform_{version}_linux_amd64.zip'.format(version=version):
            return split_line[0]

 
def file_already_exists(fname: str):
    """
    Determines if a given file already exists.
    Used for determining if we should replace an existing file.
    """
    return os.path.exists(fname) and os.path.isfile(fname)


def sha_256_verify(fname: str, sha_256_sum: str):
    """
    Verifies that a file matches a given SHA 256 hex-dump.
    """
    # Create the Hashlib object
    h = hashlib.sha256()
    
    try:
        # Hash the file we are given
        with open(fname, 'rb') as f:
            h.update(f.read())
    except FileNotFoundError:
        return None

    # Compare the given hexdigest with the one we generated
    return h.hexdigest() == sha_256_sum


def make_bin_default(new_path, default_fname=TERRAFORM_BINARY):
    """
    Sets a given path as the default Terraform binary.
    Does this by sym-linking `new_path` to `/var/opt/cloudbolt/terraform/bin/terraform`
    """
    set_progress('Setting {} as the default Terraform {}'.format(new_path, default_fname))
    try:
        set_progress('Symlinking {} -> {}'.format(new_path, default_fname))
        os.symlink(new_path, default_fname)
    except FileExistsError:
        os.remove(default_fname)
        set_progress('Symlinking {} -> {}'.format(new_path, default_fname))
        os.symlink(new_path, default_fname)


def is_linux_binary(fpath):
    """
    Reads a magic byte and determines if the file given is a Linux (ELF) binary.
    """
    with open(fpath, 'rb') as f:
        return f.read(4) == b'\x7fELF'
