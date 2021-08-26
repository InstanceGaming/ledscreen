import argparse
import logging

from tinyrpc.dispatch import RPCDispatcher
import utils
import zmq
from tinyrpc.server import RPCServer
from tinyrpc.protocols.msgpackrpc import MSGPACKRPCProtocol
from tinyrpc.transports.zmq import ZmqServerTransport
from api import Screen


LOG = logging.Logger('screend')
utils.configure_logger(LOG)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Manages all drawing to the LED screen')
    ap.add_argument('-c', '--config',
                    type=str,
                    metavar='PATH',
                    dest='config',
                    default='screen.toml',
                    help='Location of configuration TOML file.')
    ap.add_argument(type=str,
                    metavar='URL',
                    dest='rpc_url',
                    help='A URL for the RPC subsystem to bind to.')
    cla = ap.parse_args()
    config_path = cla.config
    rpc_url = cla.rpc_url

    config = utils.load_config(config_path)
    utils.validate_config(config_path, config)

    screen = Screen(
        config['width'],
        config['height'],
        config['gpio_pin'],
        config['frequency'],
        config['dma_channel'],
        config['max_brightness'],
        config['inverted'],
        config['gpio_channel'],
        fonts_dir=config['fonts_dir'],
        antialiasing=config['antialiasing'],
        frames_dir=config.get('frames_dir')
    )

    dispatcher = RPCDispatcher()
    dispatcher.register_instance(screen)
    transport = ZmqServerTransport.create(zmq.Context(), rpc_url)

    rpc_server = RPCServer(
        transport,
        MSGPACKRPCProtocol(),
        dispatcher
    )

    LOG.info('Serving...')
    rpc_server.serve_forever()
