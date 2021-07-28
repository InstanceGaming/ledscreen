import inspect

from .utils import *
from .ipc_common import ClearFrame, FillFrame, RenderFrame, SetPixelFrame, DrawTextFrame
import zmq


def _simulate_function(*args):
    args_text = ", ".join(args) if len(args) > 0 else ''
    function_name = '__UNKNOWN__'

    try:
        function_name = inspect.stack()[1][3]
    except ValueError:
        pass

    print(f'simulator: {function_name}({args_text})')


class Screen:
    @property
    def width(self):
        """
        Horizontal pixel count.
        """
        return self._w

    @property
    def height(self):
        """
        Vertical pixel count.
        """
        return self._h

    @property
    def pixel_count(self):
        """
        Get the screen area in pixels.
        """
        return self._w * self._h

    @property
    def center_point(self) -> Tuple:
        """
        Get the center point of the screen.

        :return: A coordinate in the form of a tuple (x, y)
        :rtype: tuple
        """
        return int(self._w / 2), int(self._h / 2)

    def __init__(self, w: int, h: int):
        self._w = w
        self._h = h

    def render(self):
        """
        Draw all pixel color data to the screen.
        """
        _simulate_function()

    def set_pixel(self, position: Union[Tuple, int], color: int, multiplier=1):
        """
        Change an individual LED to a color.

        :param position: apply only to the LED at this position (either x, y coordinates or index)
        :param color: color integer including all three channels, red, green and blue
        :param multiplier: scale all color channels by this mount
        """
        verify_position(position, self._w, self._h)
        adjust_color(color, multiplier)
        _simulate_function(position, color, multiplier)

    def draw_text(self,
                  position: Union[Tuple, int],
                  text: str,
                  size: int,
                  color: int,
                  background=None,
                  bold=False,
                  italic=False):
        """
        Draw characters to the screen using the current font.

        :param position: apply only to the LED at this position (either x, y coordinates or index)
        :param color: color integer including all three channels, red, green and blue
        :param background: background color where :class:`None` is transparent
        :param size: number of pixels to scale the font character
        :param text: the sequence of characters to display
        :param bold: use bolded character set
        :param italic: use italicized character set
        """
        verify_position(position, self._w, self._h)
        fix_text(text)
        check_font_size(size)
        _simulate_function(position, text, size, color, background, bold, italic)

    def fill(self, color: int, multiplier=1):
        """
        Uniformly fill the screen with a particular color.

        :param color: color integer including all three channels, red, green and blue
        :param multiplier: scale all color channels by this mount
        """
        adjust_color(color, multiplier)
        _simulate_function(color, multiplier)

    def clear(self):
        """
        Clears the screen to black.
        """
        _simulate_function()


class RemoteScreen(Screen):

    def __init__(self, socket, w: int, h: int):
        super().__init__(w, h)
        self._sock = socket

    def _send_data(self, b: bytes):
        self._sock.send(b, zmq.NOBLOCK)

    def render(self):
        """
        Draw all pixel color data to the screen.
        """
        payload = RenderFrame.encode()
        self._send_data(payload)

    def set_pixel(self, position: Union[Tuple, int], color: int, multiplier=1):
        """
        Change an individual LED to a color.

        :param position: apply only to the LED at this position (either x, y coordinates or index)
        :param color: color integer including all three channels, red, green and blue
        :param multiplier: scale all color channels by this mount
        """
        index = verify_position(position, self._w, self._h)
        final_color = adjust_color(color, multiplier)
        payload = SetPixelFrame.encode(index, final_color)
        self._send_data(payload)

    def draw_text(self,
                  position: Union[Tuple, int],
                  text: str,
                  size: int,
                  color: int,
                  background=None,
                  bold=False,
                  italic=False):
        """
        Draw characters to the screen using the current font.

        :param position: apply only to the LED at this position (either x, y coordinates or index)
        :param color: color integer including all three channels, red, green and blue
        :param background: background color where :class:`None` is transparent
        :param size: number of pixels to scale the font character
        :param text: the sequence of characters to display
        :param bold: use bolded character set
        :param italic: use italicized character set
        """
        index = verify_position(position, self._w, self._h)
        message = fix_text(text)
        check_font_size(size)
        payload = DrawTextFrame.encode(index,
                                       text,
                                       color,
                                       background,
                                       size,
                                       bold=bold,
                                       italic=italic)
        self._send_data(payload)

    def fill(self, color: int, multiplier=1):
        """
        Uniformly fill the screen with a particular color.

        :param color: color integer including all three channels, red, green and blue
        :param multiplier: scale all color channels by this mount
        """
        final_color = adjust_color(color, multiplier)
        payload = FillFrame.encode(final_color)
        self._send_data(payload)

    def clear(self):
        """
        Clears the screen to black.
        """
        payload = ClearFrame.encode()
        self._send_data(payload)
