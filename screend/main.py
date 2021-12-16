import zmq
import utils
import logging
import argparse
from api import Screen
from tinyrpc.server import RPCServer
from tinyrpc.dispatch import RPCDispatcher
from tinyrpc.transports.zmq import ZmqServerTransport
from tinyrpc.protocols.msgpackrpc import MSGPACKRPCProtocol


VERSION = '1.0.1'
LOG = logging.Logger('screend')
utils.configure_logger(LOG)


def startup_banner(scr: Screen, cnf):
    ip_addr = None
    try:
        ip_addr = utils.get_ip_address(cnf['iface'])
    except Exception as e:
        LOG.warning(f'failed to get IPv4 address: {str(e)}')

    scr.clear()
    scr.set_font('slkscr.ttf', 9, None)
    scr.draw_text(0,
                  0,
                  0xFFFFFF,
                  f'V{VERSION}',
                  'lt',
                  None,
                  'left',
                  None,
                  None)
    scr.draw_text(scr.width() - 1,
                  0,
                  0xFFFFFF,
                  'JLJ',
                  'rt',
                  None,
                  'right',
                  None,
                  None)
    if ip_addr is not None:
        parts = ip_addr.split('.')

        for i, part in enumerate(parts, start=1):
            scr.draw_text(0,
                          6 * i,
                          0x00FFFF,
                          (part if i == len(parts) else f'{part}.'),
                          'lt',
                          None,
                          'left',
                          None,
                          None)
    else:
        scr.draw_text(0,
                      6,
                      0x0000FF,
                      'BAD IFN',
                      'lt',
                      None,
                      'left',
                      None,
                      None)
    scr.render()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Manages all drawing to the '
                                             'LED screen')
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

    startup_banner(screen, config)

    dispatcher = RPCDispatcher()
    dispatcher.register_instance(screen)
    transport = ZmqServerTransport.create(zmq.Context(), rpc_url)

    rpc_server = RPCServer(
        transport,
        MSGPACKRPCProtocol(),
        dispatcher
    )

    LOG.info('serving...')
    rpc_server.serve_forever()
