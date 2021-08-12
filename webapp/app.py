import eventlet
eventlet.monkey_patch()

import signal
import flask
import logging
import pluggram
import wsio
import system
from api import Screen
from utils import load_config, configure_logger
from flask_minify import minify


LOG = logging.getLogger('ledscreen')
configure_logger(LOG)


def create_app():
    config = load_config()
    LOG.info(f'loaded application config')

    programs = pluggram.load(config['app.programs_dir'], 1)
    LOG.info(f'loaded {len(programs)} pluggrams')

    system.init(config, programs)
    LOG.debug('initialized global objects')

    app = flask.Flask(__name__)
    app.url_map.strict_slashes = False
    app.secret_key = config['app.secret']

    LOG.debug('initialized flask')

    from routes import authentication, management, endpoints

    app.register_blueprint(authentication.bp)
    app.register_blueprint(management.bp)
    app.register_blueprint(endpoints.bp)
    LOG.debug('registered blueprints')

    if config['app.minification']:
        LOG.debug('minification enabled')
        minify(app)

    socketio = wsio.init_flask(app)
    LOG.debug('initialized socket io')

    return socketio, app, config


sio, application, configuration = create_app()


def _signal_interrupt(_a, _b):
    exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, _signal_interrupt)
    host = configuration['server.host']
    port = configuration['server.port']
    LOG.info(f'starting web server {host}:{port}')
    sio.run(application, host=host, port=port)
