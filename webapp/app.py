import rpc
import zmq
import flask
import common
import signal
import logging
from utils import (load_config,
                   get_config_path,
                   validate_config,
                   configure_logger)
from tinyrpc import RPCClient
from flask_minify import minify
from tinyrpc.transports.zmq import ZmqClientTransport
from tinyrpc.protocols.msgpackrpc import MSGPACKRPCProtocol


VERSION = '1.0.0'
LOG = logging.getLogger('ledscreen')
configure_logger(LOG)


def create_app():
    config_path = get_config_path()
    conf = load_config(config_path)
    validate_config(config_path, conf)
    LOG.info(f'loaded application config')

    context = zmq.Context()

    pluggram_client = RPCClient(
        MSGPACKRPCProtocol(),
        ZmqClientTransport.create(context, conf['app.pluggramd_url'])
    )
    pluggram_proxy = pluggram_client.get_proxy()
    plugman = rpc.PluggramManager(pluggram_proxy)

    LOG.info(f'started pluggram RPC client')

    app = flask.Flask(__name__)
    app.url_map.strict_slashes = False
    app.secret_key = conf['app.secret']
    LOG.debug('initialized flask')

    common.config = conf
    common.pluggram_manager = plugman

    from routes import endpoints, management, authentication

    app.register_blueprint(authentication.bp)
    app.register_blueprint(management.bp)
    app.register_blueprint(endpoints.bp)
    LOG.debug('registered blueprints')

    if conf['app.minification']:
        LOG.debug('minification enabled')
        minify(app)

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
