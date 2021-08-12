import logging
import system
from flask import request
from flask_socketio import Namespace, SocketIO


LOG = logging.getLogger('ledscreen.wsio')


class AdminSocket(Namespace):

    def on_connect(self):
        if system.is_user_authenticated():
            LOG.info(f'admin connected {request.sid}')
            return True

        LOG.info(f'admin connect refused (not logged in) {request.sid}')
        return False

    def on_disconnect(self):
        LOG.debug(f'admin disconnected')


ADMIN_SOCKET = AdminSocket('/admin')


def init_flask(app):
    # noinspection PyUnreachableCode
    if __debug__:
        socketio = SocketIO(app=app,
                            ping_timeout=60,
                            ping_interval=30,
                            logger=True,
                            engineio_logger=True)
    else:
        socketio = SocketIO(app=app,
                            ping_timeout=240,
                            ping_interval=120)

    socketio.on_namespace(ADMIN_SOCKET)

    return socketio

