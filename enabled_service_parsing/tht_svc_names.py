#!/usr/bin/env python

import os
import re
import sys
from subprocess import check_output
import requests
import yaml

THT="/home/saravanan/KRS/work/openstack/repo/check-in/tripleo-heat-templates"
DEP=os.path.join(THT, "deployment")
CMN="/home/saravanan/KRS/work/openstack/repo/check-in/tripleo-common/container-images"
CMN_TMPL="overcloud_containers.yaml.j2"
CMN_MAP="tht_service_mapping.yaml"
UPSTREAM="https://raw.githubusercontent.com/openstack/tripleo-common/master/container-images/overcloud_containers.yaml.j2"
# No images associated with this service
SPECIAL = [
    "OS::TripleO::Services::NeutronCorePlugin",
    "OS::TripleO::Services::ComputeNeutronOvsDpdk",
    "OS::TripleO::Services::HAProxyPublicTLS",
    "OS::TripleO::Services::HAProxyInternalTLS",
]
fmap = {}

validSvcTypes = []
r = requests.get(UPSTREAM)
upstreamData = r.content.decode("utf-8")
if r.status_code == 200:
    data = r.content.decode("utf-8").split("\n")
    for line in data:
        if "OS::TripleO::Services" in line:
            m = re.search(r'.*(OS::TripleO::Services::[a-zA-Z0-9]*)$', line)
            if m and m.groups():
                validSvcTypes.append(m.group(1))

for dirName, subDirList, fileList in os.walk(DEP):
    for i in fileList:
        if not (i.endswith('.yaml') or i.endswith('.yml')):
            continue
        if i in fmap:
            print("ERROR (%s) is already parsed" % i)
            sys.exit(1)
        path = os.path.join(dirName, i)
        with open(path) as f:
            data = f.read().split('\n')
            for line in data:
                if 'service_name:' in line:
                    m = re.search(r'^ *service_name: *([a-zA-Z0-9-_]*)$', line)
                    if m and m.groups():
                        fmap[i] = {'name': m.group(1), 'path': path}
                    else:
                        fmap[i] = {'error': line, 'path': path}
                    break

noServiceType = []
notFound = []
invalidFormat = []

for k,v in fmap.items():
    kmodified = k
    if 'j2' in k:
        ks = k.split('.')
        kmodified = ks[0] + '.' + ks[2]
    try:
        cmd = ["grep", "-RnH", kmodified, THT, "--exclude-dir=.git", "--exclude-dir=tripleo_heat_templates.egg-info"]
        out = check_output(cmd)
        outs = out.decode("utf-8") 
        for line in outs.split("\n"):
            if 'OS::TripleO::Services::' in line:
                m = re.search(r'OS::TripleO::Services::([a-zA-Z0-9]*):', line)
                if m and m.groups():
                    if 'mapped' not in fmap[k]:
                        fmap[k]['mapped'] = []
                    if m.group(1) not in fmap[k]['mapped']:
                        fmap[k]['mapped'].append(m.group(1))
    except Exception as e:
        #import traceback
        #traceback.print_exc()
        #print("Exception: %s" % e)
        notFound.append(k)

lines = []
for k,v in fmap.items():
    if 'mapped' not in v:
        if '-base' not in k:
            noServiceType.append(k)
        continue
    if 'name' not in v and 'error' in v:
        invalidFormat.append(k)
        continue
    elif 'name' not in v:
        print("File %s has errors" % k)
    for i in v['mapped']:
        typ = "OS::TripleO::Services::" + i
        if typ in validSvcTypes:
            lines.append("  %s: %s" % (typ, v['name']))

with open(os.path.join(CMN, CMN_MAP), 'w') as f:
    f.write("service_type_name_map:\n")
    lines = list(set(lines))
    lines.sort()
    f.write('\n'.join(lines))

print("NoServiceType: %s\n" % ", ".join(noServiceType))
print("NOTFOUND: %s\n" % ", ".join(notFound))
print("INVALIDFORMAT: %s\n" % ", ".join(invalidFormat))

cmnMappingError = []
def getServiceName(serviceType):
    items = []
    for k, v in fmap.items():
        if 'mapped' in v and 'name' in v:
            for i in v['mapped']:
                if i == serviceType and v['name'] not in items:
                    items.append(v['name'])
    if len(items) > 1:
        print("Multiple mapping for service type (%s) - %s" % (serviceType, items))
    if len(items) == 1:
        return items[0]

special = []
for i in SPECIAL:
    m = re.search(r'OS::TripleO::Services::([a-zA-Z]*)$', i)
    if m and m.groups():
        special.append(m.group(1))

outData = []
with open(os.path.join(CMN, CMN_TMPL)) as f:
    #data = f.read().split("\n")
    data = upstreamData.split("\n")
    svcPerEntry = []
    for line in data:
        if 'services:' in line:
            line = "  service_names:"
            svc_per_entry = []
        if 'OS::TripleO::Services::' in line:
            m = re.search(r'- OS::TripleO::Services::([a-zA-Z]*)$', line)
            if m and m.groups():
                serviceType = m.group(1)
                if serviceType in special:
                    continue
                serviceName = getServiceName(serviceType)
                if serviceName in svc_per_entry:
                    continue
                svcPerEntry.append(serviceName)
                if serviceName:
                    line = ('  - %s' % serviceName)
                else:
                    cmnMappingError.append('OS::TripleO::Services::' + serviceType)
        outData.append(line)

with open(os.path.join(CMN, CMN_TMPL + '.new'), 'w') as f:
    f.write('\n'.join(outData))

cmnMappingError = list(set(cmnMappingError))
if cmnMappingError:
    print("TripleO Service Name is not found for these service Types:\n%s" % "\n".join(cmnMappingError))

