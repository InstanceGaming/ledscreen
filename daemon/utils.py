import subprocess
import threading
import time
import random
import os
import pytoml
import logging
from dotted.collection import DottedDict
from typing import Tuple, Union, NoReturn, Callable


MAX_COLORS = 16777215


def get_config_path():
    return os.environ.get('LS_CONFIG')


def _config_node_or_exit(config: DottedDict, key: str):
    value = config.get(key)
    if value is None:
        logging.error(f'"{key}" path must be defined in config')
        exit(3)
    return value


def load_config():
    config_path = get_config_path()

    if config_path is None:
        logging.error('LS_CONFIG environment variable is not set')
        exit(20)

    config = None

    if os.path.isfile(config_path):
        try:
            with open(config_path, 'r') as cf:
                config = DottedDict(pytoml.load(cf))
        except OSError as e:
            logging.error(f'open("{config_path}") failed: {str(e)}')
            exit(1)
        except pytoml.TomlError as e:
            logging.error(f'config parse failed: {str(e)}')
            exit(2)
    else:
        logging.error(f'config missing at "{config_path}"')
        exit(1)

    _config_node_or_exit(config, 'development_server')
    _config_node_or_exit(config, 'development_server.host')
    _config_node_or_exit(config, 'development_server.port')

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

    _config_node_or_exit(config, 'database')
    _config_node_or_exit(config, 'database.uri')
    _config_node_or_exit(config, 'screen')
    _config_node_or_exit(config, 'screen.width')
    _config_node_or_exit(config, 'screen.height')
    _config_node_or_exit(config, 'screen.max_brightness')
    _config_node_or_exit(config, 'screen.frequency')
    _config_node_or_exit(config, 'screen.dma_channel')
    _config_node_or_exit(config, 'screen.gpio_pin')
    _config_node_or_exit(config, 'screen.gpio_channel')
    _config_node_or_exit(config, 'screen.inverted')

    _config_node_or_exit(config, 'ipc')
    _config_node_or_exit(config, 'ipc.rx')
    _config_node_or_exit(config, 'ipc.tx')

    return config


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


def fix_text(message, encoding='UTF-8'):
    if isinstance(message, str):
        return message
    else:
        return str(message, encoding)


def text_dimensions(message: str, size: int, bold=False, italic=False) -> Tuple[int, int]:
    message = fix_text(message)
    size = check_font_size(size)
    w = 0
    h = 0
    # todo
    return w, h


def normalize_color(color: int) -> int:
    if color is None:
        color = 0

    if color > MAX_COLORS or color < 0:
        raise ValueError('color value must be within range 0-{}, was {}'.format(MAX_COLORS, color))

    # todo: normalize color value to within the capabilities of the screen
    return color


def adjust_color(color: int, multiplier: int) -> int:
    color_adjusted = normalize_color(color)
    check_multiplier(multiplier)

    r = int((0xFF0000 & color_adjusted) * multiplier)
    g = int((0x00FF00 & color_adjusted) * multiplier)
    b = int((0x0000FF & color_adjusted) * multiplier)

    return r + g + b


def check_multiplier(multiplier: int) -> NoReturn:
    # multiplier being None is the same as 1
    if multiplier is not None:
        if multiplier > 1:
            raise ValueError('multiplier value must be within range 0-1, was {}'.format(multiplier))


def position_to_index(position: Union[Tuple, int], w: int, h: int) -> NoReturn:
    count = w * h
    # enforce either x, y coordinates or index
    if isinstance(position, int):
        if position > count or position < 0:
            raise ValueError('index must be within range 0-{}, was {}'.format(count, position))
        return position
    elif isinstance(position, tuple):
        if len(position) == 2:
            x = position[0]
            y = position[1]
            if x > w:
                raise ValueError('x value must be within range 0-{}, was {}'.format(w, x))
            elif y > h:
                raise ValueError('y value must be within range 0-{}, was {}'.format(h, y))
            # todo: make this actually work
            return x * y
        raise ValueError('position tuple does not have a size of 2')
    raise ValueError('position argument has invalid structure')


def check_font_size(size: int) -> NoReturn:
    if size is None:
        raise ValueError('font size cannot be none')

    if size not in range(0, 1000):
        raise ValueError('font size must be within range 0-1000, was {}'.format(size))


def timing_counter():
    return time.perf_counter() * 1000
