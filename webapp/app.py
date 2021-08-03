import eventlet
eventlet.monkey_patch()

import signal
import flask
import logging
import common
import database
import pluggram
import wsio
from utils import load_config, configure_logger
from flask_minify import minify
from sqlalchemy.exc import SQLAlchemyError


LOG = logging.getLogger('ledscreen')
configure_logger(LOG)
configure_logger(logging.getLogger('sqlalchemy'), prod_level=logging.WARNING)
configure_logger(logging.getLogger('sqlalchemy.engine.Engine'), prod_level=logging.WARNING)


def create_app():
    config = load_config()
    LOG.info(f'loaded application config')

    app = flask.Flask(__name__)
    programs = pluggram.load(config['app.programs_dir'], 1)
    LOG.info(f'loaded {len(programs)} pluggrams')

    app.url_map.strict_slashes = False
    app.config['SQLALCHEMY_DATABASE_URI'] = config['database.uri']
    app.secret_key = config['app.secret']

    common.init(config)
    # todo: add pluggram manager object to common
    LOG.debug('initialized common objects')

    # todo: show version text on screen

    from routes import authentication, management

    app.register_blueprint(authentication.bp)
    app.register_blueprint(management.bp)
    LOG.debug('registered blueprints')

    try:
        database.init_flask(app)
        LOG.debug('initialized database')
    except SQLAlchemyError as e:
        LOG.error(f'failed to initialize database: {str(e)}')
        exit(10)

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
    LOG.info(f'starting development server {host}:{port}')
    sio.run(application, host=host, port=port)
