import logging
import threading
import zmq
import api
import ipc_common as ipc
import utils

_IPC_SERVER_EXIT_EVENT = threading.Event()
_IPC_THREAD = None


def get_context(rx_uri, tx_uri):
    zmq_context = zmq.Context()

    try:
        zmq_rxs = zmq_context.socket(zmq.PULL)
        zmq_rxs.bind(rx_uri)
        zmq_txs = zmq_context.socket(zmq.PUSH)
        zmq_txs.connect(tx_uri)
    except zmq.ZMQError as e:
        logging.error(f'IPC bind error: {str(e)}')
        exit(20)


def ipc_server(exit_event: threading.Event(), screen: api.Screen, rx, tx, receive_timeout: int):
    poller = zmq.Poller()
    poller.register(rx, zmq.POLLIN)
    while True:
        if len(poller.poll(receive_timeout)) > 0:
            message = rx.recv()
            data, frame_type, error = ipc.decode(message)
            before = utils.timing_counter()
            if error is None:
                if frame_type == ipc.StandardFrame.SESSION_INFO:
                    user_id = data
                    logging.info(f'IPC user "{user_id}"')
                    tx.send(ipc.ScreenInfoFrame.encode(screen.width, screen.height), zmq.NOBLOCK)
                    logging.info(f'IPC sent screen info')
                elif frame_type == ipc.StandardFrame.CLEAR:
                    screen.clear()
                elif frame_type == ipc.StandardFrame.RENDER:
                    screen.render()
                elif frame_type == ipc.StandardFrame.SET_PIXEL:
                    index = data[0]
                    color = data[1]

                    screen.set_pixel(index, color)
                else:
                    logging.warning(f'IPC unhandled frame type "{frame_type}"')
            else:
                logging.warning(f'IPC decoding error: {error.name} for {frame_type.name} frame')
            after = utils.timing_counter()
            delta = after - before
            logging.debug(f'IPC "{frame_type.name}" handled in {delta:0.2f}ms')

        if exit_event.isSet():
            rx.close()
            tx.close()
            break


def start_ipc_thread(screen: api.Screen, rx, tx, receive_timeout: int):
    thread = threading.Thread(target=ipc_server, args=[_IPC_SERVER_EXIT_EVENT,
                                                       screen,
                                                       rx,
                                                       tx,
                                                       receive_timeout])
    thread.daemon = True
    thread.start()
    return thread


def kill_ipc_thread():
    global _IPC_SERVER_EXIT_EVENT
    _IPC_SERVER_EXIT_EVENT.set()
