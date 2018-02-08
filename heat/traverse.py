#!/usr/bin/env python

import os
import yaml

from keystoneauth1 import loading
from keystoneauth1 import session
from heatclient import client
from keystoneauth1.identity import v3


def resource_nested_identifier(rsrc):
    nested_link = [l for l in rsrc.links or []
                   if l.get('rel') == 'nested']
    if nested_link:
        nested_href = nested_link[0].get('href')
        nested_identifier = nested_href.split("/")[-2:]
        return nested_identifier[0]


def get_heat_client():
    if os.environ['OS_IDENTITY_API_VERSION'] == '3':
        # keystone v3
        password = v3.PasswordMethod(username=os.environ['OS_USERNAME'],
                                     password=os.environ['OS_PASSWORD'],
                                     user_domain_name=os.environ['OS_USER_DOMAIN_NAME'])
        auth = v3.Auth(auth_url=os.environ['OS_AUTH_URL'] + 'v3',
                       auth_methods=[password],
                       project_name=os.environ['OS_PROJECT_NAME'],
                       project_domain_name=os.environ['OS_PROJECT_DOMAIN_NAME'])
        sess = session.Session(auth=auth)
    else:
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(auth_url=os.environ['OS_AUTH_URL'],
                                        username=os.environ['OS_USERNAME'],
                                        password=os.environ['OS_PASSWORD'],
                                        project_name=os.environ[
                                            'OS_PROJECT_NAME'],
                                        project_domain_name=os.environ['OS_PROJECT_DOMAIN_NAME'])
        sess = session.Session(auth=auth)

    heat = client.Client('1', session=sess)
    return heat


def get_resource_obj(heat, resource):
    rsrc_obj = {}
    rsrc_obj['restype'] = resource.resource_type
    #print("%s -> %s" % (resource.resource_name, resource.required_by()))
    #if type(resource) != list:
    #    rsrc_obj['required_by'] = resource.required_by()
    nested_stack = resource_nested_identifier(resource)
    if nested_stack:
        stacktree = {}
        traverse(heat, nested_stack, stacktree)
        if stacktree:
            rsrc_obj['nested'] = stacktree
    return {resource.resource_name: rsrc_obj}


def traverse(heat, stack_name, stacktree):
    res_obj = []
    resources = heat.resources.list(stack_name)
    for resource in resources:
        res_obj.append(get_resource_obj(heat, resource))

    if res_obj:
        stacktree[stack_name] = res_obj


def main():
    heat = get_heat_client()
    stacktree = {}
    traverse(heat, 'overcloud', stacktree)
    print(yaml.safe_dump(stacktree, default_flow_style=False,
                         encoding='utf-8', allow_unicode=True))

if __name__ == '__main__':
    main()
