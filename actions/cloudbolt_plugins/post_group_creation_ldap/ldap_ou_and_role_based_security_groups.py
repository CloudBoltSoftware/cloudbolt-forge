"""
Plugin to create LDAP objects when a new CB group is created
"""

import ldap
import ldap.modlist as modlist
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import sys
sys.path.append('/opt/cloudbolt')
from utilities.logger import ThreadLogger
from utilities.models import LDAPUtility
logger = ThreadLogger(__name__)


def LDAP_bind(LDAP):
    LDAP_url = '{}://{}:{}'.format(
        LDAP.protocol, LDAP.ip, LDAP.port)
    bind = ldap.initialize(LDAP_url)
    bind.bind_s(LDAP.serviceaccount, LDAP.servicepasswd)
    return(bind)


def create_security_group(bind, dn, name):
    dn = 'CN=' + name + ',' + dn
    attrs = {}
    attrs['objectClass'] = ['top', 'group']
    attrs['name'] = name
    # the groupType value may differ between ldap systems
    # this value can be found with an ldap browser
    attrs['groupType'] = '-2147483640'
    attrs['cn'] = name
    attrs['sAMAccountName'] = name
    print attrs
    ldif = modlist.addModlist(attrs)
    print ldif
    new_security_group = bind.add_s(dn, ldif)
    return new_security_group


def create_ou(bind, dn, name):
    dn = 'OU=' + name + ',' + dn
    attrs = {}
    attrs['objectClass'] = ['top', 'organizationalUnit']
    attrs['name'] = name
    print attrs
    ldif = modlist.addModlist(attrs)
    print ldif
    new_ou = bind.add_s(dn, ldif)
    return new_ou


def run(group, *args, **kwargs):
    name = str(group.name)
    logger.debug(
        'Running hook for new group "{}"'.format(name)
    )
    LDAP = LDAPUtility.objects.get(ldap_domain='cloudbolt.com')
    bind = LDAP_bind(LDAP)
    base_dn = 'OU=Customers,OU=Customer Accounts,DC=cloudbolt,DC=com'

    # Create an OU base on the CloudBolt group name
    create_ou(bind, dn=base_dn, name=name)

    # Create Security Groups for each role in the new OU
    new_dn = 'OU=' + name + ',' + base_dn
    create_security_group(bind, dn=new_dn, name=name + ' CB Viewer')
    create_security_group(bind, dn=new_dn, name=name + ' CB Approver')
    create_security_group(bind, dn=new_dn, name=name + ' CB Requestor')
    create_security_group(bind, dn=new_dn, name=name + ' CB Resource Admin')
    bind.unbind_s()
    return "", "", ""

if __name__ == '__main__':
    group_id = sys.argv[1]
    from accounts.models import Group
    group = Group.objects.get(id=group_id)
    print run(group)
