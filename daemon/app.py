import signal
import flask
import logging
import common
import database
import pluggram
from utils import load_config
from flask_minify import minify
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix


def configure_logger(log):
    handler = logging.StreamHandler()

    # noinspection PyUnreachableCode
    if __debug__:
        log.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter('{levelname:>8}: {message} [{name}@{lineno}]',
                              datefmt='%x %H:%M:%S',
                              style='{'))
    else:
        log.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter('{levelname:>8}: {message}', style='{'))

    log.handlers.clear()
    log.addHandler(handler)


LOG = logging.getLogger('ledscreen')
configure_logger(LOG)


def create_app():
    config = load_config()
    LOG.info(f'loaded application config')

    app = flask.Flask(__name__)
    programs = pluggram.load(config['app.programs_dir'], 1)
    LOG.info(f'loaded {len(programs)} pluggrams')

    app.url_map.strict_slashes = False
    app.config['SQLALCHEMY_DATABASE_URI'] = config['database.uri']
    app.secret_key = config['app.secret']
    app.wsgi_app = ProxyFix(app.wsgi_app)

    common.init(app, config, programs)
    LOG.debug('initialized common objects')

    # todo: show version text on screen

    from routes import authentication, management, workspaces, restful, oobe

    app.register_blueprint(authentication.bp)
    app.register_blueprint(management.bp)
    app.register_blueprint(workspaces.bp)
    app.register_blueprint(restful.bp)
    app.register_blueprint(oobe.bp)
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

    # configure Werkzeug logger to be quiet
    werk_log = logging.getLogger('werkzeug')
    werk_log.setLevel(logging.WARNING)

    return app, config


application, configuration = create_app()


def _signal_interrupt(_a, _b):
    exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, _signal_interrupt)

    application.run(
        configuration['development_server.host'],
        configuration['development_server.port']
    )
