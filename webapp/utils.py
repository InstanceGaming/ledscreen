import datetime
import subprocess
import threading
import time
import random
import os
import pytoml
import logging
from urllib.parse import urlparse
from dotted.collection import DottedDict
from typing import Tuple, Union, NoReturn, Callable, Iterable

LOG = logging.getLogger('ledscreen.utils')
MAX_COLORS = 16777215
DEV_FORMATTER = logging.Formatter('{levelname:>8}: {message} [{name}@{lineno}]',
                                  datefmt='%x %H:%M:%S',
                                  style='{')
FORMATTER = logging.Formatter('{levelname:>8}: {message}', style='{')


def configure_logger(log, prod_level=logging.INFO):
    handler = logging.StreamHandler()

    # noinspection PyUnreachableCode
    if __debug__:
        log.setLevel(logging.DEBUG)
        handler.setFormatter(DEV_FORMATTER)
    else:
        log.setLevel(logging.INFO)
        handler.setFormatter(FORMATTER)

    log.handlers.clear()
    log.addHandler(handler)


def get_url_port(url_text: str) -> Union[None, int]:
    try:
        return urlparse(url_text).port
    except ValueError:
        return None


def get_config_path():
    return os.environ.get('LS_CONFIG')


def _config_node_or_exit(config: DottedDict, key: str):
    value = config.get(key)
    if value is None:
        LOG.error(f'"{key}" path must be defined in config')
        exit(3)
    return value


def load_config():
    config_path = get_config_path()

    if config_path is None:
        LOG.error('LS_CONFIG environment variable is not set')
        exit(20)

    config = None

    if os.path.isfile(config_path):
        try:
            with open(config_path, 'r') as cf:
                config = DottedDict(pytoml.load(cf))
        except OSError as e:
            LOG.error(f'open("{config_path}") failed: {str(e)}')
            exit(1)
        except pytoml.TomlError as e:
            LOG.error(f'config parse failed: {str(e)}')
            exit(2)
    else:
        LOG.error(f'config missing at "{config_path}"')
        exit(1)

    _config_node_or_exit(config, 'server')
    _config_node_or_exit(config, 'server.host')
    _config_node_or_exit(config, 'server.port')

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
    _config_node_or_exit(config, 'sandbox.api_dist')
    _config_node_or_exit(config, 'sandbox.default_modules')

    if not isinstance(config['sandbox.default_modules'], Iterable):
        LOG.error(f'{config_path}: "sandbox.default_modules" must be iterable')
        exit(3)

    _config_node_or_exit(config, 'database')
    _config_node_or_exit(config, 'database.uri')
    _config_node_or_exit(config, 'screen')
    _config_node_or_exit(config, 'screen.width')
    _config_node_or_exit(config, 'screen.height')
    _config_node_or_exit(config, 'screen.frequency')
    _config_node_or_exit(config, 'screen.brightness')
    _config_node_or_exit(config, 'screen.dma_channel')
    _config_node_or_exit(config, 'screen.gpio_pin')
    _config_node_or_exit(config, 'screen.gpio_channel')
    _config_node_or_exit(config, 'screen.inverted')
    _config_node_or_exit(config, 'screen.fonts_dir')

    if not os.path.isdir(config['screen.fonts_dir']):
        LOG.error(f'{config_path}: "screen.fonts_dir" must be a valid directory')
        exit(3)

    _config_node_or_exit(config, 'ipc')
    _config_node_or_exit(config, 'ipc.rx')

    if get_url_port(config['ipc.rx']) is None:
        LOG.error(f'{config_path}: "ipc.rx" must define a port number')
        exit(3)

    return config


def pretty_elapsed_ms(before, now):
    return pretty_ms(now - before)


def pretty_ms(milliseconds):
    if milliseconds is not None:
        if milliseconds <= 1000:
            if isinstance(milliseconds, float):
                return '{:04.2f}ms'.format(milliseconds)
            return '{:04d}ms'.format(milliseconds)
        elif 1000 < milliseconds <= 60000:
            seconds = milliseconds / 1000
            return '{:02.2f}s'.format(seconds)
        elif milliseconds > 60000:
            minutes = milliseconds / 60000
            return '{:02.2f}min'.format(minutes)
    return None


def pretty_timedelta(td, prefix=None, format_spec=None):
    prefix = prefix or ''
    format_spec = format_spec or '02.2f'

    if td is not None:
        seconds = td.total_seconds()
        if seconds < 60:
            return prefix + format(seconds, format_spec) + ' seconds'
        elif 60 <= seconds < 3600:
            return prefix + format(seconds / 60, format_spec) + ' minutes'
        elif 3600 <= seconds < 86400:
            return prefix + format(seconds / 3600, format_spec) + ' hours'
        elif 86400 <= seconds:
            return prefix + format(seconds / 86400, format_spec) + ' days'
    return None


def enum_name_or_null(e):
    return e.name if e is not None else None


def isoformat_or_null(d):
    return d.isoformat() if d is not None else None


def popen_with_callback(popen_args: list, completion_cb: Callable, timeout=None):
    def runner(_args, _cb, _timeout):
        inner_process = subprocess.Popen(_args)
        inner_process.wait(_timeout)
        _cb(inner_process)
        return

    thread = threading.Thread(target=runner, args=(popen_args, completion_cb, timeout))
    thread.start()
    return thread


def generate_sanitized_alphanumerics(length: int, lowercase=True, special=False):
    char_set = 'BCDFGHJKLMNPQRSTVWXYZ0123456789'

    if lowercase:
        char_set += 'bcdfghjklmnpqrstvwxyz'

    if special:
        char_set += '_-'

    result = ''

    for i in range(length):
        result += random.choice(char_set)

    return result


def generate_url_binary(length: int):
    return random.randbytes(int(round(length/2))).hex()


def check_font_size(size: int, bold=False) -> NoReturn:
    """
    Check if the current font size is possible.
    :param size: Desired font size.
    :param bold: If the font should be considered in bold.
    :raises ValueError: If the font cannot be displayed at this size.
    """
    if size is None:
        raise ValueError('font size cannot be none')

    if size not in range(0, 1000):
        raise ValueError('font size must be within range 0-1000, was {}'.format(size))


def combine_rgb(r: int, g: int, b: int):
    return (r << 16) | (g << 8) | b


def timing_counter():
    """
    perf_counter() in milliseconds.
    """
    return time.perf_counter() * 1000
