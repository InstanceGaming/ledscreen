import subprocess
import threading
import time
import random
import os
import pytoml
import logging
from dotted.collection import DottedDict, DottedList
from typing import Callable


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


def get_config_path():
    return os.environ.get('LS_CONFIG')


class ConfigValidator:

    def __init__(self, path, data: DottedDict, parent=None, node_name=None):
        self._path = path
        self._data = data
        self._parent = parent
        self._name = node_name
        self._validators = []

    def addValidator(self, node_name: str):
        sv = ConfigValidator(self._path, self._data, self, node_name)
        self._validators.append(sv)
        return sv

    def getAbsoluteKey(self, relative_key: str):
        if self._parent is None:
            raise NotImplementedError('Cannot validate root-level nodes')
        else:
            if self._name is None:
                raise RuntimeError('Sub-validator was never given name')

        if '.' in relative_key:
            raise KeyError('Relative key cannot change depth (contain dots)')

        return '.'.join([self._name, relative_key])

    def getValue(self, relative_key: str):
        abs_key = self.getAbsoluteKey(relative_key)
        return self._data.get(abs_key)

    def validate(self, relative_key: str, required_type=None):
        abs_key = self.getAbsoluteKey(relative_key)

        if abs_key in self._data:
            value = self._data[abs_key]

            if required_type is not None:
                if not isinstance(value, required_type):
                    LOG.error(f'"{abs_key}" must be of type {required_type.__name__}')
                    exit(3)
        else:
            LOG.error(f'"{abs_key}" must be defined')
            exit(3)


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

    root = ConfigValidator(config_path, config)

    server = root.addValidator('server')
    server.validate('host', str)
    server.validate('port', int)
    server.validate('iface', str)

    app = root.addValidator('app')
    app.validate('secret', str)
    app.validate('programs_dir', str)
    app.validate('minification', bool)
    app.validate('api_keys', DottedList)
    app.validate('max_session_minutes', int)

    user = root.addValidator('user')
    user.validate('name', str)
    user.validate('password', str)

    screen = root.addValidator('screen')
    screen.validate('width', int)
    screen.validate('height', int)
    screen.validate('frequency', int)
    screen.validate('brightness', int)
    screen.validate('dma_channel', int)
    screen.validate('gpio_pin', int)
    screen.validate('gpio_channel', int)
    screen.validate('inverted', bool)
    screen.validate('fonts_dir', str)

    fonts_dir = screen.getValue('fonts_dir')

    if fonts_dir is not None:
        if not os.path.isdir(fonts_dir):
            LOG.error(f'{config_path}: "screen.fonts_dir" must be a valid directory')
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
            return prefix + format(seconds, format_spec) + ' sec'
        elif 60 <= seconds < 3600:
            return prefix + format(seconds / 60, format_spec) + ' min'
        elif 3600 <= seconds < 86400:
            return prefix + format(seconds / 3600, format_spec) + ' hr'
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


def combine_rgb(r: int, g: int, b: int):
    return (r << 16) | (g << 8) | b


def canonical_filename(directory: str, name: str):
    for file in os.listdir(directory):
        if file.lower().strip() == name.lower().strip():
            return file
    return None


def timing_counter():
    """
    perf_counter() in milliseconds.
    """
    return time.perf_counter() * 1000
