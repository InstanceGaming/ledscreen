import subprocess
import threading
from typing import Tuple, Union, NoReturn, Callable
import time
import random


MAX_COLORS = 16777215


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
