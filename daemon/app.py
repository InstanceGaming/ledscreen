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


logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s][%(module)s:%(lineno)s]: %(message)s')


def create_app():
    config = load_config()
    logging.info(f'loaded application config')

    app = flask.Flask(__name__)
    programs = pluggram.load(config['app.programs_dir'], 1)
    logging.info(f'loaded {len(programs)} pluggrams')

    app.url_map.strict_slashes = False
    app.config['SQLALCHEMY_DATABASE_URI'] = config['database.uri']
    app.secret_key = config['app.secret']
    app.wsgi_app = ProxyFix(app.wsgi_app)

    common.init(app, config, programs)
    logging.debug('initialized common objects')

    from routes import authentication, management, workspaces, restful, oobe

    app.register_blueprint(authentication.bp)
    app.register_blueprint(management.bp)
    app.register_blueprint(workspaces.bp)
    app.register_blueprint(restful.bp)
    app.register_blueprint(oobe.bp)
    logging.debug('registered blueprints')

    try:
        database.init_flask(app)
        logging.debug('initialized database')
    except SQLAlchemyError as e:
        logging.error(f'failed to initialize database: {str(e)}')
        exit(10)

    if config['app.minification']:
        logging.debug('minification enabled')
        minify(app)

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
