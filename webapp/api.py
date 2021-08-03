import logging
import os
import pathlib
from functools import lru_cache
from typing import Tuple
from PIL import Image, ImageFont, ImageDraw

import utils

LOG = logging.getLogger('ledscreen.api')

try:
    import rpi_ws281x

    _LED_STRIP_CLASS = rpi_ws281x.PixelStrip
except ModuleNotFoundError:
    from dummy_ws281x import DummyStrip

    _LED_STRIP_CLASS = DummyStrip

MAX_BRIGHTNESS = 196


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
    def center(self):
        return int(round(self._w / 2)), int(round(self._h / 2))

    def __init__(self,
                 w: int,
                 h: int,
                 output_pin: int,
                 frequency: int,
                 dma_channel: int,
                 brightness: int,
                 invert_signal: bool,
                 gpio_channel: int,
                 fonts_dir: str):
        super().__init__()

        self._logger = logging.getLogger()
        self._w = w
        self._h = h
        self._output_pin = output_pin
        self._font_dir = os.path.abspath(fonts_dir)
        self._cached_fonts = {'default': ImageFont.load_default()}
        self._current_font = self._cached_fonts['default']
        self._canvas = self._create_image('RGB', 0)
        self._painter = ImageDraw.Draw(self._canvas)
        self._matrix = _LED_STRIP_CLASS(self.pixel_count,
                                        self._output_pin,
                                        frequency,
                                        dma_channel,
                                        invert_signal,
                                        brightness,
                                        gpio_channel)
        self.set_brightness(brightness)
        self._matrix.begin()

    def _create_image(self, mode: str, color_data):
        return Image.new(mode, (self._w, self._h), color_data)

    def render(self):
        for i, (r, g, b) in enumerate(self._canvas.getdata()):
            self._matrix.setPixelColor(i, utils.combine_rgb(r, g, b))

        self._matrix.show()

    def set_pixel(self, xy: int, color: int):
        self._painter.point(xy, fill=color)

    def set_brightness(self, v: int):
        if v > 255 or v < 0:
            raise ValueError('Brightness must be within range 0-255')

        if v > MAX_BRIGHTNESS:
            raise RuntimeError('Too much current would be drawn with given global brightness amount, '
                               'crashed to prevent blowing all the supply fuses')

        self._matrix.setBrightness(v)
        LOG.debug('screen brightness changed ({})'.format(v))

    def set_font(self, name: str, size=None, font_face=None) -> bool:
        name = name.lower().strip()

        if name == 'default':
            self._current_font = self._cached_fonts['default']
            return True

        if size is None:
            raise ValueError('Font size is required for all non-default fonts')

        if name in self._cached_fonts.keys():
            self._current_font = self._cached_fonts[name]
            return True
        else:
            try:
                font_path = os.path.join(self._font_dir, name)
                ext = pathlib.Path(font_path).suffix

                if ext == '.ttf':
                    self._current_font = ImageFont.truetype(font_path, size, font_face or 0)
                    LOG.info(f'loaded TrueType font "{name}"')
                else:
                    self._current_font = ImageFont.load(font_path)
                    LOG.info(f'loaded font "{name}"')

                self._cached_fonts.update({name: self._current_font})
                return True
            except OSError:
                LOG.debug(f'failed to load font "{name}" from "{self._font_dir}"')

        return False

    @lru_cache(100)
    def text_dimensions(self, message: str) -> Tuple:
        """
        Get the x, y size of text with a given message.
        :param message: character sequence to consider
        :return: width, height
        """
        a, b = self._current_font.getsize(message)
        return a, b

    def index_of(self, x: int, y: int):
        if x < 0 or y < 0:
            raise ValueError('Coordinates cannot be negative')

        if y > self._h:
            raise IndexError(f'Y coordinate cannot be larger than {self._h}')

        return x + y * self._w

    def draw_text(self,
                  xy,
                  color: int,
                  message: str,
                  anchor=None,
                  spacing=None,
                  alignment=None,
                  stroke_width=None,
                  stroke_fill=None):
        """
        Draw text into the current frame to be rendered.
        See https://pillow.readthedocs.io/en/stable/handbook/text-anchors.html#text-anchors for more details on anchoring.

        :param x: x coordinate
        :param y: y coordinate up to screen height
        :param color: foreground color (what the text will be filled with)
        :param message: characters to draw from the current font
        :param anchor: anchoring position (graph origin) of the text, "lt" or "la" (default)
        :param spacing: number of pixels between lines
        :param alignment: relative alignment of characters, "left", "center", "right"
        :param stroke_width: number of pixels that form a outline around each character
        :param stroke_fill: color of outline around each character
        """
        assert isinstance(xy, tuple)
        self._painter.text(xy,
                           message,
                           fill=color,
                           font=self._current_font,
                           anchor=anchor,
                           spacing=spacing,
                           align=alignment,
                           stroke_width=stroke_width or 0,
                           stroke_fill=stroke_fill)

    def fill(self, color: int):
        self._canvas = self._create_image('RGB', color)
        self.render()

    def clear(self):
        self.fill(0)

    def write_file(self, filename: str):
        self._canvas.save(filename)
