import os
import time
import pytoml
import logging
from dotted.collection import DottedDict


LOG = logging.getLogger('ledscreen.utils')
DEV_FORMATTER = logging.Formatter('{levelname:>8}: {message} [{name}@{lineno}]',
                                  datefmt='%x %H:%M:%S',
                                  style='{')
FORMATTER = logging.Formatter('{levelname:>8}: {message}', style='{')


def configure_logger(log):
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
            return relative_key
        else:
            if self._name is None:
                raise RuntimeError('Sub-validator was never given name')

        if '.' in relative_key:
            raise KeyError('Relative key cannot change depth (contain dots)')

        return '.'.join([self._name, relative_key])

    def getValue(self, relative_key: str):
        abs_key = self.getAbsoluteKey(relative_key)
        return self._data.get(abs_key)

    def validate(self,
                 relative_key: str,
                 required_type=None,
                 optional=False,
                 isdir=False):
        abs_key = self.getAbsoluteKey(relative_key)

        if abs_key in self._data:
            value = self._data[abs_key]

            if required_type is not None:
                if not isinstance(value, required_type):
                    LOG.error(f'"{abs_key}" must be of type '
                              f'{required_type.__name__}')
                    exit(3)
                else:
                    if isdir and not os.path.isdir(value):
                        LOG.error(f'"{abs_key}" must be a directory')
                        exit(3)
        else:
            if not optional:
                LOG.error(f'"{abs_key}" must be defined')
                exit(3)


def load_config(path: str):
    config = None

    if os.path.isfile(path):
        try:
            with open(path, 'r') as cf:
                config = DottedDict(pytoml.load(cf))
        except OSError as e:
            LOG.error(f'open("{path}") failed: {str(e)}')
            exit(1)
        except pytoml.TomlError as e:
            LOG.error(f'config parse failed: {str(e)}')
            exit(2)
    else:
        LOG.error(f'config missing at "{path}"')
        exit(1)

    return config


def validate_config(path: str, config: DottedDict):
    root = ConfigValidator(path, config)
    root.validate('width', int)
    root.validate('height', int)
    root.validate('frequency', int)
    root.validate('max_brightness', int)
    root.validate('dma_channel', int)
    root.validate('gpio_pin', int)
    root.validate('gpio_channel', int)
    root.validate('inverted', bool)
    root.validate('antialiasing', bool)
    root.validate('fonts_dir', str, isdir=True)
    root.validate('frames_dir', str, optional=True, isdir=True)


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
