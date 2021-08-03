import logging
from flask import request
from flask_socketio import Namespace, SocketIO
from models import UserType
from routes.authentication import auth_endpoint_allowed


LOG = logging.getLogger('ledscreen.wsio')


class AdminSocket(Namespace):

    def on_connect(self):
        if auth_endpoint_allowed(minimum_credential=UserType.ADMIN):
            LOG.info(f'admin connected {request.sid}')
            return True

        LOG.info(f'admin connect refused (invalid AID) {request.sid}')
        return False

    def on_disconnect(self):
        LOG.debug(f'admin disconnected')


ADMIN_SOCKET = AdminSocket('/admin')


def init_flask(app):
    # noinspection PyUnreachableCode
    if __debug__:
        socketio = SocketIO(app=app,
                            ping_timeout=120,
                            ping_interval=60,
                            logger=True,
                            engineio_logger=True)
    else:
        socketio = SocketIO(app=app,
                            ping_timeout=120,
                            ping_interval=60)

    for sock in SOCKETS:
        socketio.on_namespace(sock)

    return socketio

