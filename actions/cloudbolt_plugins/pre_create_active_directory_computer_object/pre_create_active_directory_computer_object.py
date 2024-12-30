"""
This CloudBolt Plugin should be used as an Orchestration action at the
Pre-Create Resource Hook Point. It will pre-create a computer account in the
specified OU in the LDAP server. This should be used in conjunction with the
Domain to join parameter that is available in the CloudBolt UI when creating a
new server. When the server is powered on, the Domain to join function will
pass the domain credentials to the customization spec in vCenter, which will
then join the server to the domain, since the computer account has been
pre-created, when the guest joins the domain, the computer account will be
in the expected OU.

Setup:
1. Create an Orchestration Hook at the Pre-Create Resource Hook Point using this
    plugin.
2. Create a new Parameter in CloudBolt called domain_ou_dn
3. Add the domain_to_join and domain_ou_dn parameters to Environment, Blueprint
    or Group (depending on what makes sense for your use case).
4. When creating a new server, set the Domain to join parameter to the domain
    you want to join and set the domain_ou_dn parameter to the DN of the OU you
    want the computer account to be created in.
"""
from common.methods import set_progress
from utilities.logger import ThreadLogger
import ldap.modlist as modlist
import ldap
from utilities.models import LDAPUtility

logger = ThreadLogger(__name__)


def run(job, server=None, *args, **kwargs):
    computer_name = server.hostname
    ldap_util = server.get_cfv_for_custom_field("domain_to_join")
    ou_dn = server.get_cfv_for_custom_field("domain_ou_dn")
    if not ldap_util or not ou_dn:
        logger.info("Skipping pre-creating computer account in LDAP because "
                    "domain_to_join or domain_ou_dn is not set.")
        return "SUCCESS", "", ""
    ldap_util = ldap_util.value
    ou_dn = ou_dn.value
    create_ldap_computer_account(ldap_util, computer_name, ou_dn)
    return "SUCCESS", "", ""


def create_ldap_computer_account(ldap_util, computer_name, ou_dn):
    # Computer details
    sAMAccountName = f"{computer_name}$"  # Append $ to indicate a computer account
    computer_dn = f"CN={computer_name},{ou_dn}"

    # Attributes for the computer object
    attributes = {
        "objectClass": [b"top", b"person", b"organizationalPerson", b"user",
                        b"computer"],
        "cn": [computer_name.encode()],
        "sAMAccountName": [sAMAccountName.encode()],
        # sAMAccountName should include the $ for computer accounts
        "userAccountControl": [b"4096"],  # 4096 = WORKSTATION_TRUST_ACCOUNT
    }

    try:
        # Connect to the LDAP server
        conn = ldap_util._initialize_ldap()
        conn.set_option(ldap.OPT_REFERRALS, 1)  # Enable referral following
        conn.simple_bind_s(ldap_util.serviceaccount, ldap_util.servicepasswd)

        # Prepare the LDIF format for the new entry
        ldif = modlist.addModlist(attributes)

        # Add the new entry
        set_progress(f"Creating computer account {computer_name} in {ou_dn}...")
        conn.add_s(computer_dn, ldif)
        logger.debug(f"Computer account {computer_name} created successfully "
                     f"in {ou_dn}.")

        # Close the connection
        conn.unbind_s()

    except ldap.LDAPError as e:
        print(f"LDAP error: {e}")