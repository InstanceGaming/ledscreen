import logging
import threading
import zmq
import api
import ipc_common as ipc
import utils

LOG = logging.getLogger('ledscreen.ipc')
_IPC_SERVER_EXIT_EVENT = threading.Event()
_IPC_THREAD = None


def ipc_server(exit_event: threading.Event(), screen: api.Screen, rx, receive_timeout: int):
    poller = zmq.Poller()
    poller.register(rx, zmq.POLLIN)
    while True:
        if len(poller.poll(receive_timeout)) > 0:
            message = rx.recv()
            data, frame_type, error = ipc.decode(message)
            before = utils.timing_counter()
            if error is None:
                if frame_type == ipc.StandardFrame.CLEAR:
                    screen.clear()
                elif frame_type == ipc.StandardFrame.RENDER:
                    screen.render()
                elif frame_type == ipc.StandardFrame.SET_PIXEL:
                    index = data[0]
                    color = data[1]

                    screen.set_pixel(index, color)
                else:
                    LOG.warning(f'IPC unhandled frame type "{frame_type}"')
            else:
                LOG.warning(f'IPC decoding error: {error.name} for {frame_type.name} frame')
            after = utils.timing_counter()
            delta = after - before
            LOG.debug(f'IPC "{frame_type.name}" handled in {delta:0.2f}ms')

        if exit_event.isSet():
            rx.close()
            break


def start_ipc_thread(screen: api.Screen, rx, receive_timeout: int):
    thread = threading.Thread(target=ipc_server, args=[_IPC_SERVER_EXIT_EVENT,
                                                       screen,
                                                       rx,
                                                       receive_timeout])
    thread.daemon = True
    thread.start()
    return thread


def kill_ipc_thread():
    global _IPC_SERVER_EXIT_EVENT
    _IPC_SERVER_EXIT_EVENT.set()
