from typing import Tuple, Union, NoReturn
import time


MAX_COLORS = 16777215


def timing_counter():
    """
    A monotonic, high-precision system counter. Useful for timing events.

    :return: an integer counter relative only to itself.
    """
    return time.perf_counter() * 1000


def text_dimensions(message: str, size: int, bold=False, italic=False) -> Tuple[int, int]:
    """
    Get the dimensions of a message as shown on the screen.

    :param message: a string that comprises your desired message.
    :param size: font size in pixels.
    :param bold: calculate the font with bolded weight.
    :param italic: calculate the font with italicized characters.
    :return: a tuple containing the (x, y) size of the message.
    """
    message = fix_text(message)
    size = check_font_size(size)
    w = 0
    h = 0
    # todo
    return w, h


def fix_text(message, encoding='UTF-8'):
    """
    Internal. Coerce strings from message object.

    :param message: message object.
    :return: the message if it was already a string, otherwise the UTF-8 str() representation.
    """
    if isinstance(message, str):
        return message
    else:
        return str(message, encoding)


def normalize_color(color: int) -> int:
    """
    Normalize color value to be more balanced.

    :param color: original user-supplied color.
    :return: normalized color value.
    """

    if color is None:
        color = 0

    if color > MAX_COLORS or color < 0:
        raise ValueError('color value must be within range 0-{}, was {}'.format(MAX_COLORS, color))

    # todo: normalize color value to within the capabilities of the screen
    return color


def adjust_color(color: int, multiplier: int) -> int:
    """
    Factor color multiplier and normalize.

    :param color: original user-supplied color.
    :param multiplier: an intensity factor 0-1.
    :return: adjusted and scaled color value.
    """
    color_adjusted = normalize_color(color)
    check_multiplier(multiplier)

    r = int((0xFF0000 & color_adjusted) * multiplier)
    g = int((0x00FF00 & color_adjusted) * multiplier)
    b = int((0x0000FF & color_adjusted) * multiplier)

    return r + g + b


def check_multiplier(multiplier: int) -> NoReturn:
    """
    Internal. Enforce multiplier range (0-1).

    :param multiplier: value to be checked.
    """
    # multiplier being None is the same as 1
    if multiplier is not None:
        if multiplier > 1:
            raise ValueError('multiplier value must be within range 0-1, was {}'.format(multiplier))


def verify_position(position, w: int, h: int) -> NoReturn:
    """
    Internal. Enforce either (x, y) coordinates or single-integer format for screen positioning.

    :param position: value to be checked.
    :param w: width of the screen instance.
    :param h: height of the screen instance.
    """
    count = w * h
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


def check_font_size(size: int, bold=False) -> NoReturn:
    """
    Determine if font supports given size and styling options.

    :param size: desired font size to check.
    :param bold: consider the font when bolded.
    :raises ValueError: when the font does not support these parameters.
    """
    if size is None:
        raise ValueError('font size cannot be none')

    if size not in range(0, 1000):
        raise ValueError('font size must be within range 0-1000, was {}'.format(size))
