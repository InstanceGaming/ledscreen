from .utils import *
from .ipc_common import ClearFrame, FillFrame, RenderFrame, SetPixelFrame, DrawTextFrame
import zmq


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
        raise NotImplementedError()

    def __init__(self, socket, w: int, h: int):
        self._sock = socket
        self._w = w
        self._h = h

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
        index = position_to_index(position, self._w, self._h)
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
        index = position_to_index(position, self._w, self._h)
        message = fix_text(text)
        check_font_size(size)
        payload = DrawTextFrame.encode(index,
                                       color,
                                       background,
                                       size,
                                       message,
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
