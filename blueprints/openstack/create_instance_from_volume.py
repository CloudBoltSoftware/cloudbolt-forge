import openstack
from openstack import connection
from infrastructure.models import CustomField, Environment
from utilities.models import ConnectionInfo
from resourcehandlers.openstack.models import OpenStackHandler
from infrastructure.models import CustomField
from common.methods import set_progress


CONN = ConnectionInfo.objects.get(name='Openstack')
assert isinstance(CONN, ConnectionInfo)

AUTH_URL = '{}://{}:{}/v3'.format(CONN.protocol, CONN.ip, CONN.port)


def generate_creds():
   rh = OpenStackHandler.objects.first()
   conn = connection.Connection(
     region_name='RegionOne',
     auth=dict(auth_url= AUTH_URL,
     username=rh.serviceaccount, password=rh.servicepasswd,
     project_id=rh.project_id,
     user_domain_id=rh.domain),
     compute_api_version='2.1', identity_interface='public', verify=False)
   return conn


def generate_options_for_volume(server=None, **kwargs):
    conn = generate_creds()
    volumes = conn.list_volumes()
    return [(vol.name) for vol in volumes]


def generate_options_for_image(server=None, **kwargs):
    conn = generate_creds()
    images = conn.list_images()
    return [(image.name) for image in images]


def generate_options_for_flavor(server=None, **kwargs):
    conn = generate_creds()
    flavors = conn.list_flavors()
    return [(flavor.name) for flavor in flavors]


def generate_options_for_network(server=None, **kwargs):
    conn = generate_creds()
    networks = conn.list_networks()
    return [(net.name) for net in networks]


def generate_options_for_security_group(server=None, **kwargs):
    conn = generate_creds()
    groups = conn.list_security_groups()
    return [(group.name) for group in groups]


def generate_options_for_key_pair_name(server=None, **kwargs):
    conn = generate_creds()
    keys = conn.list_keypairs()
    return [(key.name) for key in keys]


def generate_options_for_availability_zone(server=None, **kwargs):
    conn = generate_creds()
    zones = conn.list_availability_zone_names()
    return [(zone) for zone in zones]


def generate_options_for_floating_ips(**kwargs):
    conn = generate_creds()
    floating_ips = conn.list_floating_ips()
    return [(ip.floating_ip_address) for ip in floating_ips]


def generate_options_for_cloudbolt_environment(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Openstack").values("id", "name")
    return [(env['id'], env['name']) for env in envs]


def get_floating_ip_pool(**kwargs):
    conn = generate_creds()
    pool_list = conn.list_floating_ip_pools()
    return [p['name'] for p in pool_list]

def create_required_custom_fields():
    CustomField.objects.get_or_create(
        name='env_id',
        defaults={
            'label': 'Environment ID',
            'description': 'Used by Openstack blueprint',
            'type': 'INT',
        }
    )
    CustomField.objects.get_or_create(
        name='server_name', defaults={
            'label': 'Instance name', 'type': 'STR',
            'description': 'Name of the openstack BP instance',
        }
    )
    CustomField.objects.get_or_create(
        name='volume', defaults={
            'label': 'volume name', 'type': 'STR',
            'description': 'Name of the openstack bootable volume',
        }
    )

def run(job, logger=None, **kwargs):
    resource = kwargs.get('resource')

    env_id = '{{ cloudbolt_environment }}'
    env = Environment.objects.get(id=env_id)

    env.resource_handler.cast()
    name = '{{ hostname }}'
    volume = '{{ volume }}'
    flavor = '{{ flavor }}'
    network = '{{ network }}'
    security_group = '{{ security_group }}'
    key_name = '{{ key_pair_name }}'
    availability_zone = '{{ availability_zone }}'
    floating_ip = '{{ floating_ips }}'
    pool = get_floating_ip_pool()
    conn = generate_creds()
    server = conn.create_server(
            name=name,
            flavor=flavor,
            boot_volume=volume,
            network=network,
            key_name=key_name,
            security_groups=security_group,
            )
    conn.wait_for_server(server, ips=floating_ip, ip_pool=pool, timeout=180)
    set_progress("Creating OpenStack node '{}' from boot volume '{}'".format(
            name, volume)
        )

    # Save cluster data on the resource
    create_required_custom_fields()
    resource = kwargs['resource']
    resource.env_id = env_id
    resource.server_name = name
    resource.volume = volume
    resource.name = name
    resource.save()

    return "SUCCESS","Openstack instance created with name '{}',flavor '{}', network '{}', " \
                     "key pair '{}', boot volume '{}', floating ip '{}', security_group(s) '{}'".format(
               name, flavor, network, key_name, volume, floating_ip, security_group), ""
