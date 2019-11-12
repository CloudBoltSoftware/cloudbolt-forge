"""
This plugin prepares the given servers for RKE and creates an RKE config file
"""
import os
import time

import yaml

from common.methods import set_progress
from utilities.exceptions import CommandExecutionException
from utilities.logger import ThreadLogger
from utilities import run_command

import settings

# set this if `rke` is not in your PATH
PATH_TO_RKE_EXECUTABLE = None
logger = ThreadLogger(__name__)


def create_ssh_keypair(size=2048):
    """
    Make a new ssh keypair of a given size
    :param: size (optional, defaults to 2048). How many bits large should the key be?
    :return: UTF-8 strings representing the public key and private key in that order
    """
    from cryptography.hazmat.primitives import serialization as crypto_serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend as crypto_default_backend

    key = rsa.generate_private_key(
        backend=crypto_default_backend(),
        public_exponent=65537,
        key_size=size,
    )

    private_key = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption())

    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH,
        crypto_serialization.PublicFormat.OpenSSH
    )

    return public_key.decode('utf-8'), private_key.decode('utf-8')


def generate_rke_yaml(ips, user, ssh_private_key):
    """
    Make the YAML file that RKE is going to use to create the kubernetes cluster
    :param ips: What IP addresses are we working with? Array of strings
    :param user: What user should we create?
    :param ssh_private_key: Private key text (utf-8) to include in yaml
    :return: string with the formatted yaml in it
    """
    nodes = []
    for ip in ips:
        nodes.append(
            {
                'address': ip,
                'user': user,
                'ssh_key': ssh_private_key,
                'role': [],
            },
        )
    for i, role in enumerate(['controlplane', 'etcd']):
        node_idx = i % len(nodes)
        nodes[node_idx]['role'].append(role)

    for node in nodes:
        if len(node['role']) == 0:
            node['role'].append('worker')

    worker_count = 0
    for node in nodes:
        if 'worker' in node['role']:
            worker_count += 1

    if worker_count == 0:
        for node in nodes:
            if 'controlplane' not in node['role']:
                node['role'].append('worker')
                worker_count += 1
    if worker_count == 0:
        nodes[0]['role'].append('worker')

    etcd_count = 0
    for node in nodes:
        if 'etcd' in node['role']:
            etcd_count += 1
    if etcd_count < 3:
        for node in nodes:
            if 'etcd' not in node['role'] and 'controlplane' not in node['role']:
                node['role'].append('etcd')
                etcd_count += 1
                if etcd_count >= 3:
                    break

    services = {
        'etcd': {'image': 'quay.io/coreos/etcd:latest'},
        'kube-api': {'image': 'rancher/k8s:v1.11.6-rancher2'},
        'kube-controller': {'image': 'rancher/k8s:v1.11.6-rancher2'},
        'scheduler': {'image': 'rancher/k8s:v1.11.6-rancher2'},
        'kubelet': {'image': 'rancher/k8s:v1.11.6-rancher2'},
        'kubeproxy': {'image': 'rancher/k8s:v1.11.6-rancher2'},
    }
    addons = [
        {
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": {
                "name": "cloudbolt-admin",
                "namespace": "kube-system"
            }
        },
        {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "ClusterRoleBinding",
            "metadata": {
                "name": "cloudbolt-admin"
            },
            "roleRef": {
                "apiGroup": "rbac.authorization.k8s.io",
                "kind": "ClusterRole",
                "name": "cluster-admin"
            },
            "subjects": [
                {
                    "kind": "ServiceAccount",
                    "name": "cloudbolt-admin",
                    "namespace": "kube-system"
                }
            ]
        },
    ]

    document = {
        'nodes': nodes,
        'services': services,
        'addons': '---\n' + yaml.dump_all(addons),
    }

    return yaml.dump(document)


def find_all_server_ips(blueprint_context):
    """
    Given the blueprint context, find the IP addresses for each server
    :param blueprint_context:
    :return: list of ip addresses represented as strings
    """
    ips = []
    for server_obj in find_all_servers(blueprint_context):
        if hasattr(server_obj, 'ip') and server_obj.ip is not None and (server_obj.ip != ''):
            ips.append(server_obj.ip)
    return ips


def find_all_servers(blueprint_context):
    """
    Given the blueprint context, find all servers
    :param blueprint_context:
    :return: iterable (yield) over Server objects
    """
    for key, value in blueprint_context.items():
        if isinstance(value, dict) and 'servers' in value:
            server_query_set = value.get('servers')
            for server_obj in server_query_set:
                yield server_obj


def prepare_server_hosts(user, blueprint_context, ssh_public_key):
    docker_script = 'yum -y install docker firewalld || exit 1;\n' + \
                    'systemctl enable docker || exit 1;\n' + \
                    'useradd {};\n'.format(user) + \
                    'groupadd docker\n' + \
                    'usermod -aG docker {} || exit 1\n'.format(user) + \
                    'mkdir -p /home/{}/.ssh || exit 1;\n'.format(user) + \
                    'echo \'{}\' >> /home/{}/.ssh/authorized_keys || exit 1;\n'.format(ssh_public_key, user) + \
                    'chown -R {} /home/{}/.ssh || exit 1;\n'.format(user, user) + \
                    'chmod 755 /home/{}/.ssh || exit 1;\n'.format(user) + \
                    'chmod 644 /home/{}/.ssh/authorized_keys || exit 1;\n'.format(user) + \
                    'echo \'net.ipv6.conf.all.forwarding=1\' >> /etc/sysctl.conf || exit 1\n' + \
                    'sysctl -p /etc/sysctl.conf || exit 1'

    # See https://github.com/coreos/coreos-kubernetes/blob/master/Documentation/kubernetes-networking.md
    # for official documentation on kubernetes networking and port useage.
    for tcp_port_num in [80, 443, 10250, 2379, 2380, 6443]:
        docker_script += '\nfirewall-offline-cmd --add-port={}/tcp || exit 1;'.format(tcp_port_num)

    for udp_port_num in [8285, 8472]:
        docker_script += '\nfirewall-offline-cmd --add-port={}/udp || exit 1;'.format(udp_port_num)

    docker_script += '\nsystemctl restart firewalld;\n'
    logger.info(f"docker script:\n{docker_script}")

    for server in find_all_servers(blueprint_context=blueprint_context):
        set_progress("Starting script execution on server {}".format(server.ip))

        try:
            server.execute_script(script_contents=docker_script, timeout=700)
        except CommandExecutionException:
            set_progress("Failed to run command. Trying again with `sudo`.")
            server.execute_script(script_contents=docker_script, timeout=700, run_with_sudo=True)

        server.reboot()

    set_progress("Waiting for server(s) to begin reboot.")
    time.sleep(10)

    for server in find_all_servers(blueprint_context=blueprint_context):
        server.wait_for_os_readiness()


def kubernetes_up(cluster_path):
    if PATH_TO_RKE_EXECUTABLE:
        cmd = f"{PATH_TO_RKE_EXECUTABLE}/rke up --config={cluster_path}/cluster.yml"
    else:
        cmd = f"rke up --config={cluster_path}/cluster.yml"

    run_command.execute_command(cmd, timeout=900, stream_title="Running rke up")
    # optional: use run_command.run_command(cmd) instead of run_command.execute_command()


def run(job, *_args, **kwargs):
    """
    main entry point for the plugin
    """

    user = 'cbrke'
    blueprint_context = kwargs.get('blueprint_context', {})
    ssh_public_key, ssh_private_key = create_ssh_keypair()
    prepare_server_hosts(user, blueprint_context, ssh_public_key)

    cluster_path = os.path.join(settings.VARDIR, "opt", "cloudbolt", "rke", f"resource-{job.parent_job.resource_set.first().id}")

    os.makedirs(cluster_path)

    with open(f"{cluster_path}/rke_private_key.pem", 'w') as fl:
        fl.write(ssh_private_key)
    with open(f"{cluster_path}/rke_public_key.pem", 'w') as fl:
        fl.write(ssh_public_key)

    ips = find_all_server_ips(kwargs.get('blueprint_context', {}))
    rke_yaml_text = generate_rke_yaml(ips, user, ssh_private_key)

    cluster_yml_name = "cluster.yml"

    with open(f"{cluster_path}/{cluster_yml_name}", 'w') as fl:
        fl.write(rke_yaml_text)

    set_progress(f"Your ssh public and private keys have been generated. Please find them in {cluster_path}")

    set_progress(f"Your RKE cluster.yml file has been generated. Please find it in {cluster_path}/{cluster_yml_name}")

    set_progress(f"Running RKE Config")
    kubernetes_up(cluster_path)

    return "SUCCESS", f"./rke up --config={cluster_path}/cluster.yml", ""