import argparse
import sys
import zmq
from .ipc_common import decode, SessionInfoFrame, ScreenInfoFrame
from .api import Screen
from .utils import *


__version__ = "1.0.0"
__author__ = "Jacob Jewett"

_SCREEN_CACHE = None


def _parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--screen-host', type=str, dest='screen_host', required=True)
    ap.add_argument('--tx-port', type=int, dest='screen_tx', required=True)
    ap.add_argument('--rx-port', type=int, dest='screen_rx', required=True)
    args, _ = ap.parse_known_args(sys.argv)
    return args


def get_screen() -> Screen:
    """
    Get the Screen object from the system.
    :return: a Screen instance
    """
    global _SCREEN_CACHE

    if _SCREEN_CACHE is None:
        cla = _parse_args()
        host = cla.screen_host
        tx_uri = f'tcp://{host}:{cla.screen_tx}'
        rx_uri = f'tcp://*:{cla.screen_rx}'

        context = zmq.Context()

        try:
            txs = context.socket(zmq.PUSH)
            txs.connect(tx_uri)

            rxs = context.socket(zmq.PULL)
            rxs.bind(rx_uri)
        except zmq.ZMQError as e:
            raise RuntimeError(f'Error establishing connection to screen daemon: {str(e)}')

        try:
            # todo: get user ID from environment
            txs.send(SessionInfoFrame.encode(1))
            response = rxs.recv()
            rxs.close()
        except zmq.ZMQError as e:
            raise RuntimeError(f'Error during handshake phase: {str(e)}')

        data, frame_type, error = decode(response)

        if error is None:
            if frame_type.SCREEN_INFO:
                width = data[0]
                height = data[1]

                _SCREEN_CACHE = api.Screen(txs, width, height)
            else:
                raise RuntimeError(f'Unexpected response during handshake phase: {frame_type.name}')
        else:
            raise RuntimeError(f'Error decoding handshake: {error.name}')

    return _SCREEN_CACHE
