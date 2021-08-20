import eventlet
eventlet.monkey_patch()

import signal
import flask
import logging
import pluggram
import wsio
import system
import netutils
from utils import load_config, configure_logger
from flask_minify import minify


LOG = logging.getLogger('ledscreen')
configure_logger(LOG)


def create_app():
    config = load_config()
    LOG.info(f'loaded application config')
    system.init(config)

    programs = pluggram.load(config['app.programs_dir'], 1)
    LOG.info(f'loaded {len(programs)} pluggrams')

    for program in programs:
        if program.has_user_options:
            program.load_options()

    LOG.info(f'loaded pluggram user settings')
    system.loaded_pluggrams.extend(programs)

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

    ip_addr = None
    try:
        ip_addr = netutils.get_ip_address(config['server.iface'])
    except Exception as e:
        LOG.warning(f'failed to get IPv4 address: {str(e)}')

    system.screen.set_font('slkscr.ttf', 9)
    system.screen.draw_text((0, 0),
                            color=0xFFFFFF,
                            message=f'V{system.VERSION}',
                            anchor='lt',
                            alignment='left')
    system.screen.draw_text((system.screen.width, 0),
                            color=0xFFFFFF,
                            message='JLJ',
                            anchor='rt',
                            alignment='right')
    if ip_addr is not None:
        parts = ip_addr.split('.')

        for i, part in enumerate(parts, start=1):
            system.screen.draw_text((0, 6 * i),
                                    color=0x00FFFF,
                                    message=(part if i == len(parts) else f'{part}.'),
                                    anchor='lt',
                                    alignment='left')
    else:
        system.screen.draw_text((0, 6),
                                color=0x0000FF,
                                message='IFP FAIL',
                                anchor='lt',
                                alignment='left')

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
