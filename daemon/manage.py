import argparse
import os
import sys
import json
import subprocess as sp


def parse_args():
    ap = argparse.ArgumentParser(description='manage led screen manually')
    sp_manager = ap.add_subparsers()
    sp_create_workspace = sp_manager.add_parser('create-workspace')
    sp_create_workspace.add_argument(nargs=1,
                                     type=str,
                                     metavar='USER',
                                     dest='user_id',
                                     help='Owner of workspace')
    sp_workspace = sp_manager.add_parser('workspace')
    sp_workspace.add_argument('--reset',
                              action='store_true',
                              dest='reset',
                              help='Reset workspace to default template')
    sp_workspace.add_argument('--run',
                              action='store_true',
                              dest='run',
                              help='Run workspace code')
    sp_workspace.add_argument('-s', '--simulate',
                              action='store_true',
                              dest='simulate',
                              help='Run workspace code using dummy driver')
    sp_workspace.add_argument('--rm',
                              action='store_true',
                              dest='remove',
                              help='Remove workspace from system')
    sp_workspace.add_argument('-P', '--purge',
                              action='store_true',
                              dest='purge',
                              help='Purge workspace files')
    sp_workspace.add_argument(nargs=1,
                              type=str,
                              metavar='WORKSPACE',
                              dest='workspace_id',
                              help='Workspace ID to operate on')
    return ap.parse_args()


def run():
    cla = parse_args()


if __name__ == '__main__':
    run()
