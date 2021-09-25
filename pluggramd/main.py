import zmq
import json
import logging
import argparse
from api import PluggramManager
from utils import configure_logger
from pluggram import load
from tinyrpc.server import RPCServer
from tinyrpc.dispatch import RPCDispatcher
from tinyrpc.transports.zmq import ZmqServerTransport
from tinyrpc.protocols.msgpackrpc import MSGPACKRPCProtocol


LOG = logging.Logger('pluggramd')
configure_logger(LOG)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Manages pluggram system')
    ap.add_argument(type=str,
                    metavar='DIRECTORY',
                    dest='programs_dir',
                    help='Location of pluggram programs.')
    ap.add_argument(type=str,
                    metavar='SCREEN_URL',
                    dest='screen_rpc_url',
                    help='RPC screen server URL.')
    ap.add_argument(type=str,
                    metavar='URL',
                    dest='rpc_url',
                    help='A URL for the RPC subsystem to bind to.')
    cla = ap.parse_args()

    programs_dir = cla.programs_dir
    screen_rpc_url = cla.screen_rpc_url
    rpc_url = cla.rpc_url

    metadata = load(programs_dir, 1)

    for md in metadata:
        try:
            md.load_options()
        except OSError as e:
            LOG.info(f'did not load user options from file for "{md.name}"')
        except json.JSONDecodeError as e:
            LOG.warning(f'failed to parse user options store for "{md.name}"')

    manager = PluggramManager(metadata, screen_rpc_url)

    dispatcher = RPCDispatcher()
    dispatcher.register_instance(manager)
    transport = ZmqServerTransport.create(zmq.Context(), rpc_url)

    rpc_server = RPCServer(
        transport,
        MSGPACKRPCProtocol(),
        dispatcher
    )

    LOG.info('serving...')
    rpc_server.serve_forever()
