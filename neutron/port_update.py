#!/usr/bin/env python

import os
import yaml
import json

from keystoneauth1 import loading
from keystoneauth1 import session
from neutronclient.v2_0 import client
from keystoneauth1.identity import v3


def get_neutron_client():
    neutron = client.Client(username=os.environ['OS_USERNAME'],
                            password=os.environ['OS_PASSWORD'],
                            project_name=os.environ['OS_PROJECT_NAME'],
                            auth_url=os.environ['OS_AUTH_URL'])
    return neutron


def fix_neutron_port_socket_path(neutron, port):
    port['binding:vif_details']['vhostuser_socket'].replace(
        '/var/run/openvswitch', '/var/lib/vhost_sockets')
    port_obj = {}
    port_obj['binding:vif_details'] = port['binding:vif_details']
    neutron.update_port(port['id'], {'port': port_obj})
    # ERROR: cannot update via REST API as 'binding:vif_details' is readonly


def main():
    neutron = get_neutron_client()
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
