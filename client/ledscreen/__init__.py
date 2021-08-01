import argparse
import sys
import zmq
import enum
from .ipc_common import decode
from .api import Screen
from .utils import *


__version__ = "1.0.0"
__author__ = "Jacob Jewett"

_SCREEN_CACHE = None


def _parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--simulate',
                    action='store_true',
                    default=False,
                    dest='simulate')
    ap.add_argument('--screen-width',
                    type=int,
                    nargs=1,
                    metavar='WIDTH',
                    dest='screen_width')
    ap.add_argument('--screen-height',
                    type=int,
                    nargs=1,
                    metavar='HEIGHT',
                    dest='screen_height')
    ap.add_argument('--screen-host',
                    type=str,
                    nargs=1,
                    metavar='HOST',
                    dest='screen_host')
    ap.add_argument('--tx-port',
                    type=int,
                    nargs=1,
                    metavar='PORT',
                    dest='screen_tx')
    args, _ = ap.parse_known_args(sys.argv)
    return args


class InternalError(enum.IntEnum):
    """
    Internal. Error codes possible from `get_screen()`.
    """
    CLI_ARGS_MISSING = 100
    """
    A required argument was never passed.
    """

    CLI_ARGS_INVALID = 200
    """
    A required argument had an unexpected value.
    """

    NO_CONNECTION = 300
    """
    Failed to connect to the screen server.
    """

    BAD_SCREEN_SIZE = 400
    """
    Width or height arguments had a value less than 1.
    """

    BAD_PORT = 500
    """
    Provided transmit port was less than 1.
    """


def _error_msg(error_type: InternalError):
    stream = sys.stderr
    print('An internal error has occurred (it was nothing you did)', file=stream)
    print(f'Please report this with error code and version to {__author__}', file=stream)
    print(f'Error code: {error_type.value:08X} {error_type.name}', file=stream)
    print(f'Version: {__version__}', file=stream)
    exit(1000)


def get_screen() -> Screen:
    """
    Get the Screen object from the system.
    Will return a :class:`RemoteScreen` when running on the physical screen.
    **This should be one of the first lines of code in your program.**

    :return: the appropriate :class:`Screen` instance
    :rtype: Screen or RemoteScreen
    """
    global _SCREEN_CACHE

    if _SCREEN_CACHE is None:
        cla = _parse_args()

        screen_width = cla.screen_width

        if screen_width is None:
            _error_msg(InternalError.CLI_ARGS_MISSING)
        elif screen_width < 1:
            _error_msg(InternalError.BAD_SCREEN_SIZE)

        screen_height = cla.screen_height

        if screen_height is None:
            _error_msg(InternalError.CLI_ARGS_MISSING)
        elif screen_height < 1:
            _error_msg(InternalError.BAD_SCREEN_SIZE)

        if cla.simulate:
            _SCREEN_CACHE = api.Screen(screen_width, screen_height)
        else:
            host = cla.screen_host

            if host is None:
                _error_msg(InternalError.CLI_ARGS_MISSING)
            elif host == '':
                _error_msg(InternalError.CLI_ARGS_INVALID)

            tx_port = cla.screen_tx

            if tx_port is None:
                _error_msg(InternalError.CLI_ARGS_MISSING)
            elif tx_port < 1:
                _error_msg(InternalError.BAD_PORT)

            tx_uri = f'tcp://{host}:{tx_port}'

            context = zmq.Context()

            try:
                txs = context.socket(zmq.PUSH)
                txs.connect(tx_uri)
                _SCREEN_CACHE = api.RemoteScreen(txs, screen_width, screen_height)
            except zmq.ZMQError:
                _error_msg(InternalError.NO_CONNECTION)

    return _SCREEN_CACHE
