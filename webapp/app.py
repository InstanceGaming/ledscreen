import signal
import flask
import logging
import rpc
import netutils
import zmq
import common
from tinyrpc import RPCClient
from tinyrpc.protocols.msgpackrpc import MSGPACKRPCProtocol
from tinyrpc.transports.zmq import ZmqClientTransport
from utils import load_config, configure_logger, validate_config, get_config_path
from flask_minify import minify

VERSION = '1.0.0'
LOG = logging.getLogger('ledscreen')
configure_logger(LOG)


def create_app():
    config_path = get_config_path()
    conf = load_config(config_path)
    validate_config(config_path, conf)
    LOG.info(f'loaded application config')

    context = zmq.Context()
    screen_client = RPCClient(
        MSGPACKRPCProtocol(),
        ZmqClientTransport.create(context, conf['app.screen_url'])
    )
    screen_proxy = screen_client.get_proxy()
    scr = rpc.Screen(screen_proxy)

    LOG.info(f'started screen RPC client')

    pluggram_client = RPCClient(
        MSGPACKRPCProtocol(),
        ZmqClientTransport.create(context, conf['app.pluggram_url'])
    )
    pluggram_proxy = pluggram_client.get_proxy()
    plugman = rpc.PluggramManager(pluggram_proxy)

    LOG.info(f'started pluggram RPC client')

    app = flask.Flask(__name__)
    app.url_map.strict_slashes = False
    app.secret_key = conf['app.secret']
    LOG.debug('initialized flask')

    common.config = conf
    common.screen = scr
    common.pluggram_manager = plugman

    from routes import authentication, management, endpoints

    app.register_blueprint(authentication.bp)
    app.register_blueprint(management.bp)
    app.register_blueprint(endpoints.bp)
    LOG.debug('registered blueprints')

    if conf['app.minification']:
        LOG.debug('minification enabled')
        minify(app)

    ip_addr = None
    try:
        ip_addr = netutils.get_ip_address(conf['server.iface'])
    except Exception as e:
        LOG.warning(f'failed to get IPv4 address: {str(e)}')

    scr.clear()
    scr.set_font('slkscr.ttf', 9)
    scr.draw_text(0,
                  0,
                  0xFFFFFF,
                  f'V{VERSION}',
                  anchor='lt',
                  alignment='left')
    scr.draw_text(scr.width,
                  0,
                  0xFFFFFF,
                  'JLJ',
                  anchor='rt',
                  alignment='right')
    if ip_addr is not None:
        parts = ip_addr.split('.')

        for i, part in enumerate(parts, start=1):
            scr.draw_text(0,
                          6 * i,
                          0x00FFFF,
                          (part if i == len(parts) else f'{part}.'),
                          anchor='lt',
                          alignment='left')
    else:
        scr.draw_text(0,
                      6,
                      0x0000FF,
                      'BAD IFN',
                      'lt',
                      'left')
    scr.render()

    return app


application = create_app()


def _signal_interrupt(_a, _b):
    exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, _signal_interrupt)
    host = common.config['server.host']
    port = common.config['server.port']
    LOG.info(f'starting web server {host}:{port}')
    application.run(host=host, port=port)
