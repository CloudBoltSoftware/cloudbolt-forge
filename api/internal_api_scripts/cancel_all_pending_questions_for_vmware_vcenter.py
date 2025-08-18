#!/usr/local/bin/python


"""
Answers all questions for all servers in a given resource handler with the
'Cancel' choice.

VMs can get in the state where they have a question that needs answering, for
instance, if its datastore has run out of free space. This script is useful to
clear out all of these questions because doing it by hand can be incredibly
tedious.
"""


import argparse

from infrastructure.models import Server
from utilities.exceptions import NotFoundException
import resourcehandlers.vmware.pyvmomi_wrapper as pyvmomi_wrapper


def get_pyvmomi_vm(uuid, rh):
    si = get_pyvmomi_si(rh)
    return pyvmomi_wrapper.get_vm_by_uuid(si, uuid)


def get_pyvmomi_si(rh):
    si = pyvmomi_wrapper.get_connection(
        rh.ip,
        rh.port,
        rh.serviceaccount,
        rh.servicepasswd,
    )
    return si


def get_args():
    parser = argparse.ArgumentParser(
        description='Cancel all pending questions for all servers in a vCenter')
    parser.add_argument(
        '-r', '--resource-handler-id',
        type=int,
        help='ID of the Resource Handler',
    )
    args = parser.parse_args()
    return args


def main(rh_id):
    for svr in Server.objects.filter(
            resource_handler_id=rh_id, status='ACTIVE').iterator():
        print
        print 'Working on server {}'.format(svr.hostname)

        rh = svr.resource_handler
        if rh.type_slug != 'vmware':
            print '  Server is not a VMware server'
            continue

        uuid = svr.resource_handler_svr_id
        try:
            vm = get_pyvmomi_vm(uuid, rh)
        except NotFoundException:
            print '  Server not found in resource handler'
            continue

        question = vm.summary.runtime.question
        if not question:
            print '  No questions found'
            continue

        # get the key for the "Cancel" choice
        for choice in question.choice:
            if choice.label == 'Cancel':
                key = choice.key
                break
        else:
            raise AssertionError('Cancel choice not found for this question')

        print '  Canceling question'
        vm.AnswerVM(question.id, key)


if __name__ == '__main__':
    args = get_args()
    main(args.resource_handler_id)
