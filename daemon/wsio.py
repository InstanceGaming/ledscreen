import logging
import stats
from flask import request
from flask_socketio import Namespace, emit, SocketIO
from models import UserType
from routes.authentication import auth_endpoint_allowed


LOG = logging.getLogger('ledscreen.wsio')


class AdminSocket(Namespace):

    def on_connect(self):
        if auth_endpoint_allowed(minimum_credential=UserType.ADMIN):
            LOG.info(f'admin connected {request.sid}')
            self.on_update_stats()
            return True

        LOG.info(f'admin connect refused (invalid AID) {request.sid}')
        return False

    def on_update_stats(self):
        students, online_students, executions = stats.get_stats()
        payload = {
            'Students': students,
            'Online': online_students,
            'Executions': executions
        }
        LOG.debug(f'updated admin portal statistics')
        emit('update_stats', payload)

    def on_disconnect(self):
        LOG.debug(f'admin disconnected')


class StudentSocket(Namespace):

    def on_connect(self):
        if auth_endpoint_allowed(minimum_credential=UserType.STUDENT):
            LOG.info(f'student connected {request.sid}')
            return True

        LOG.info(f'student connect refused (invalid AID) {request.sid}')
        return False

    def on_disconnect(self):
        LOG.debug(f'student disconnected')


ADMIN_SOCKET = AdminSocket('/admin')
STUDENT_SOCKET = StudentSocket('/student')
SOCKETS = [
    ADMIN_SOCKET,
    STUDENT_SOCKET
]


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

