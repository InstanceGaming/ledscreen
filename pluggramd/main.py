import argparse
import zmq
import logging
from utils import configure_logger
from api import PluggramManager
from tinyrpc.dispatch import RPCDispatcher
from tinyrpc.server import RPCServer
from tinyrpc.protocols.msgpackrpc import MSGPACKRPCProtocol
from tinyrpc.transports.zmq import ZmqServerTransport
from pluggram import load

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
