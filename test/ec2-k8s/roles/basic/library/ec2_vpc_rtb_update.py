#!/usr/bin/python
#
# Module that updates the routing table of a VPC.
#

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

import boto.vpc


def main():
    argument_spec = ec2_argument_spec()
    argument_spec.update(dict(
        vpc_id=dict(required=True),
        subnets=dict(type='list', required=True),
        routes=dict(type='list')
    ))

    module = AnsibleModule(argument_spec=argument_spec)

    ec2_url, aws_access_key, aws_secret_key, region = get_ec2_creds(module)

    if not region:
        module.fail_json(msg="region must be specified")

    try:
        connection = boto.vpc.connect_to_region(
            region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key)
    except boto.exception.NoAuthHandlerFound, e:
        module.fail_json(msg=str(e))

    tables = connection.get_all_route_tables(
        filters={'vpc_id': module.params.get('vpc_id')}
    )

    def match_by_subnets(t):
        subnet_ids = map(lambda x: x.subnet_id, t.associations)
        return set(subnet_ids) == set(module.params.get('subnets'))

    selected_tables = filter(match_by_subnets, tables)

    if len(selected_tables) != 1:
        if len(selected_tables) == 0:
            module.fail_json(msg="No route table found")
        else:
            module.fail_json(msg="Multiple route tables selected")

    rtb = selected_tables[0]

    changed = False
    for route in module.params.get('routes'):
        existing_rt = filter(
            lambda x: x.destination_cidr_block == route['dest'], rtb.routes)
        if len(existing_rt) > 0:
            continue
        success = connection.create_route(
            rtb.id, route['dest'], instance_id=route.get('gw'))
        if success:
            changed = True

    module.exit_json(changed=changed, rtb_id=rtb.id)

main()
