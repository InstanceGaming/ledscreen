import argparse
import signal
import flask
import logging
import os
import pytoml
import common
import random
from pluggram import load
from flask_minify import minify
from dotted.collection import DottedDict
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix
from models import UserType


logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s][%(module)s:%(lineno)s]: %(message)s')


def _config_node_or_exit(config: DottedDict, key: str):
    value = config.get(key)
    if value is None:
        logging.error(f'"{key}" path must be defined in config')
        exit(3)
    return value


def _load_config(path):
    config = None

    if os.path.isfile(path):
        try:
            with open(path, 'r') as cf:
                config = DottedDict(pytoml.load(cf))
        except OSError as e:
            logging.error(f'open("{path}") failed: {str(e)}')
            exit(1)
        except pytoml.TomlError as e:
            logging.error(f'config parse failed: {str(e)}')
            exit(2)
    else:
        logging.error(f'config missing at "{path}"')
        exit(1)

    _config_node_or_exit(config, 'development_server')
    _config_node_or_exit(config, 'development_server.host')
    _config_node_or_exit(config, 'development_server.port')

    _config_node_or_exit(config, 'app')
    _config_node_or_exit(config, 'app.secret')
    _config_node_or_exit(config, 'app.programs_dir')
    _config_node_or_exit(config, 'app.minification')

    _config_node_or_exit(config, 'default_admin')
    _config_node_or_exit(config, 'default_admin.username')
    _config_node_or_exit(config, 'default_admin.password')

    _config_node_or_exit(config, 'sandbox')
    _config_node_or_exit(config, 'sandbox.run_dir')
    _config_node_or_exit(config, 'sandbox.storage_dir')
    _config_node_or_exit(config, 'sandbox.envs_dir')
    _config_node_or_exit(config, 'sandbox.user_id')
    _config_node_or_exit(config, 'sandbox.group_id')
    _config_node_or_exit(config, 'sandbox.entrypoint')

    _config_node_or_exit(config, 'database')
    _config_node_or_exit(config, 'database.uri')
    _config_node_or_exit(config, 'screen')
    _config_node_or_exit(config, 'screen.width')
    _config_node_or_exit(config, 'screen.height')
    _config_node_or_exit(config, 'screen.max_brightness')
    _config_node_or_exit(config, 'screen.frequency')
    _config_node_or_exit(config, 'screen.dma_channel')
    _config_node_or_exit(config, 'screen.gpio_pin')
    _config_node_or_exit(config, 'screen.gpio_channel')
    _config_node_or_exit(config, 'screen.inverted')

    _config_node_or_exit(config, 'ipc')
    _config_node_or_exit(config, 'ipc.rx')
    _config_node_or_exit(config, 'ipc.tx')

    return config


def get_config_path():
    return os.environ.get('LS_CONFIG')


def create_app():
    config_path = get_config_path()

    if config_path is None:
        logging.error('LS_CONFIG environment variable is not set')
        exit(20)

    app = flask.Flask(__name__)

    config = _load_config(config_path)
    logging.info(f'loaded application config from "{config_path}"')

    progs = load(config['app.programs_dir'])

    app.url_map.strict_slashes = False
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = config['database.uri']
    app.secret_key = config['app.secret']
    app.wsgi_app = ProxyFix(app.wsgi_app)

    common.init(app, config, progs)
    logging.debug('initialized common objects')

    from routes import authentication, management, workspaces, restful

    app.register_blueprint(authentication.bp)
    app.register_blueprint(management.bp)
    app.register_blueprint(workspaces.bp)
    app.register_blueprint(restful.bp)
    logging.debug('registered blueprints')

    import models
    try:
        models.init(app)
        logging.debug('initialized database')
    except SQLAlchemyError as e:
        logging.error(f'failed to initialize database: {str(e)}')
        exit(10)

    if config['app.minification']:
        logging.debug('minification enabled')
        minify(app)

    return app, config


application, configuration = create_app()


def _get_cli_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup-db',
                        action='store_true',
                        dest='setup_db',
                        help='Do not run; create and setup database tables and default users.')
    return parser.parse_args()


def _signal_interrupt(_a, _b):
    exit(0)


def run():
    global application, configuration

    signal.signal(signal.SIGINT, _signal_interrupt)
    cla = _get_cli_args()
    setup_db_mode = cla.setup_db

    if setup_db_mode:
        import models
        import system

        try:
            models.create_all_tables(application)
            logging.info(f'created tables')
            with application.app_context():
                system.create_user(UserType.ADMIN,
                                   configuration['default_admin.username'],
                                   password=configuration['default_admin.password'])
                logging.info(f'created default admin user')
        except SQLAlchemyError as e:
            logging.error(f'failed to setup database: {str(e)}')
            exit(10)
    else:
        application.run(
            configuration['development_server.host'],
            configuration['development_server.port']
        )


if __name__ == '__main__':
    run()
