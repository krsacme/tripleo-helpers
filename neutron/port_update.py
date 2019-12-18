#!/usr/bin/env python

import os
import yaml
import json

from keystoneauth1 import loading
from keystoneauth1 import session
from neutronclient.v2_0 import client
from keystoneauth1.identity import v3

import nova.conf
from keystoneauth1 import loading as ks_loading
from neutronclient.v2_0 import client as clientv20
from oslo_utils import uuidutils
from nova import config


def get_neutron_client_for_admin():
    CONF = nova.conf.CONF
    argv = ['nova']

    config.parse_args(argv, configure_db=False, init_rpc=False)
    _SESSION = ks_loading.load_session_from_conf_options(
        CONF, nova.conf.neutron.NEUTRON_GROUP)
    auth_plugin = ks_loading.load_auth_from_conf_options(
        CONF, nova.conf.neutron.NEUTRON_GROUP)

    global_request_id = 'req-%s' % uuidutils.generate_uuid()

    #client_args = dict(session=_SESSION, auth=auth_plugin, global_request_id=context.global_request_id)
    #client_args = dict(session=_SESSION, auth=auth_plugin, global_request_id=global_request_id)
    client_args = dict(session=_SESSION, auth=auth_plugin)
    client_args = dict(client_args,
                       endpoint_override=CONF.neutron.url,
                       region_name=CONF.neutron.region_name or 'RegionOne')

    client = clientv20.Client(**client_args)
    return client


def get_neutron_client():
    neutron = client.Client(username=os.environ['OS_USERNAME'],
                            password=os.environ['OS_PASSWORD'],
                            project_name=os.environ['OS_PROJECT_NAME'],
                            auth_url=os.environ['OS_AUTH_URL'])
    return neutron


def fix_neutron_port_socket_path(neutron, port):
    port['binding:vif_details']['vhostuser_socket'].replace(
        '/var/run/openvswitch', '/var/lib/vhost_sockets')
    port['binding:vif_details']['vhostuser_mode'] = 'server'
    port_obj = {}
    port_obj['binding:vif_details'] = port['binding:vif_details']
    neutron.update_port(port['id'], {'port': port_obj})


def main():
    neutron = get_neutron_client_for_admin()
    ports = neutron.list_ports()
    for port in ports['ports']:
        if 'vhostuser_socket' in port['binding:vif_details']:
            socket_path = port['binding:vif_details']['vhostuser_socket']
            if '/var/run/openvswitch' in socket_path:
                print("Port (%s) has older socket path as (%s)" %
                      (port['id'], socket_path))
                fix_neutron_port_socket_path(neutron, port)

if __name__ == '__main__':
    main()
