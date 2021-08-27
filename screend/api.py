import io
import logging
import os
import pathlib
import utils
from io import BytesIO
from typing import Tuple, Optional, List
from PIL import Image, ImageFont, ImageDraw
from tinyrpc.dispatch import public

try:
    import rpi_ws281x

    _LED_STRIP_CLASS = rpi_ws281x.PixelStrip
except ModuleNotFoundError:
    from dummy_ws281x import DummyStrip

    _LED_STRIP_CLASS = DummyStrip


class Screen:

    # property
    @public
    def width(self):
        return self._w

    # property
    @public
    def height(self):
        return self._h

    # property
    @public
    def pixel_count(self):
        return self._w * self._h

    # property
    @public
    def center(self):
        return int(round(self._w / 2)), int(round(self._h / 2))

    # property
    def antialiasing(self):
        return self._painter.fontmode == 'L'

    # antialiasing setter
    def set_antialiasing(self, v):
        if v:
            self._painter.fontmode = 'L'
        else:
            self._painter.fontmode = '1'

    # property
    @public
    def current_font(self) -> Tuple[str, str]:
        return self._current_font.getname()

    # property
    @public
    def max_brightness(self) -> int:
        return self._max_brightness

    def __init__(self,
                 w: int,
                 h: int,
                 output_pin: int,
                 frequency: int,
                 dma_channel: int,
                 max_brightness: int,
                 invert_signal: bool,
                 gpio_channel: int,
                 fonts_dir: str,
                 antialiasing=False,
                 frames_dir=None):
        super().__init__()
        self.LOG = logging.getLogger('screend.api')
        utils.configure_logger(self.LOG)

        self._logger = logging.getLogger()
        self._w = w
        self._h = h
        self._frame_count = 1
        self._frames_dir = frames_dir
        self._output_pin = output_pin
        self._fonts_dir = os.path.abspath(fonts_dir)
        self._cached_fonts = {'default': ImageFont.load_default()}
        self._current_font = self._cached_fonts['default']
        self._canvas = self._create_canvas('RGB', 0)
        self._painter = ImageDraw.Draw(self._canvas)
        self.antialiasing = antialiasing
        self._max_brightness = max_brightness
        self._matrix = _LED_STRIP_CLASS(self.pixel_count,
                                        self._output_pin,
                                        frequency,
                                        dma_channel,
                                        invert_signal,
                                        max_brightness,
                                        gpio_channel)
        self.set_brightness(max_brightness)
        self._matrix.begin()
        self.clear()

    def _setup_painter(self):
        self._painter = ImageDraw.Draw(self._canvas)
        self._painter.fontmode = self.antialiasing

    def _set_canvas(self, mode: str, color: int):
        self._canvas = self._create_canvas(mode, color)
        self._setup_painter()

    def _create_canvas(self, mode: str, color_data):
        return Image.new(mode, (self._w, self._h), color_data)

    @public
    def paste(self, data: bytes, box: Optional[Tuple[int, int, int, int]]):
        img = Image.open(io.BytesIO(data))
        self._canvas.paste(img, box=box)

    @public
    def render(self):
        for i, (r, g, b) in enumerate(self._canvas.getdata()):
            self._matrix.setPixelColor(i, utils.combine_rgb(r, g, b))

        self._matrix.show()

        if self._frames_dir is not None:
            path = os.path.join(self._frames_dir, f'{self._frame_count}.png')
            self.write_file(path)

        self._frame_count += 1

    @public
    def set_pixel(self, x: int, y: int, color: int):
        self._painter.point((x, y), fill=color)

    @public
    def set_brightness(self, v: int):
        if v > 255 or v < 0:
            raise ValueError('Brightness must be within range 0-255')

        if v > self._max_brightness:
            raise RuntimeError('Too much current would be drawn with given global brightness amount, '
                               'crashed to prevent blowing all the supply fuses')

        self._matrix.setBrightness(v)
        self.LOG.info('screen brightness changed ({})'.format(v))

    @public
    def set_font(self, name: str, size: Optional[int], font_face: Optional[int]) -> bool:
        name = name.lower().strip()
        unique_name = name

        if size is not None:
            assert isinstance(size, int)
            unique_name += f'@{size}'

        if font_face is not None:
            assert isinstance(font_face, int)
            unique_name += f'#{font_face}'

        if size is None:
            raise ValueError('Font size is required for all non-default fonts')

        if name in self._cached_fonts.keys():
            self._current_font = self._cached_fonts[unique_name]
            return True
        else:
            try:
                canonical_name = utils.canonical_filename(self._fonts_dir, name)

                if canonical_name is None:
                    raise FileNotFoundError()

                font_path = os.path.join(self._fonts_dir, canonical_name)
                ext = pathlib.Path(font_path).suffix

                if ext == '.ttf':
                    self._current_font = ImageFont.truetype(font_path, size, font_face or 0)
                    self.LOG.info(f'loaded TrueType font "{name}"')
                else:
                    self._current_font = ImageFont.load(font_path)
                    self.LOG.info(f'loaded font "{name}"')

                self._cached_fonts.update({unique_name: self._current_font})
                return True
            except OSError:
                self.LOG.debug(f'failed to load font "{name}" from "{self._fonts_dir}"')

        return False

    @public
    def font_names(self) -> list:
        return [n.lower() for n in os.listdir(self._fonts_dir)]

    @public
    def text_dimensions(self,
                        message: str,
                        spacing: Optional[int],
                        features: Optional[List[str]],
                        stroke_width: Optional[int]) -> Tuple:
        a, b = self._painter.multiline_textsize(message,
                                                self._current_font,
                                                spacing=spacing or 4,
                                                features=features,
                                                stroke_width=stroke_width or 0)
        return a, b

    @public
    def index_of(self, x: int, y: int) -> int:
        if x < 0 or y < 0:
            raise ValueError('Coordinates cannot be negative')

        if y > self._h:
            raise IndexError(f'Y coordinate cannot be larger than {self._h}')

        return x + y * self._w

    @public
    def draw_text(self,
                  x: int,
                  y: int,
                  color: int,
                  message: str,
                  anchor: Optional[str],
                  spacing: Optional[int],
                  alignment: Optional[str],
                  stroke_width: Optional[int],
                  stroke_fill: Optional[int]):
        self._painter.text((x, y),
                           message,
                           fill=color,
                           font=self._current_font,
                           anchor=anchor,
                           spacing=spacing or 0,
                           align=alignment,
                           stroke_width=stroke_width or 0,
                           stroke_fill=stroke_fill)

    @public
    def fill(self, color: int, box: Optional[Tuple[int, int, int, int]]):
        if box is not None:
            if not isinstance(box, tuple):
                raise ValueError('box must be a tuple of structure (x1, y1, x2, y2)')

            if len(box) != 4:
                raise ValueError('box must be a tuple of structure (x1, y1, x2, y2)')

        self._painter.rectangle(box or (0, 0, self._w, self._h), fill=color)

    @public
    def draw_ellipse(self,
                     x: int,
                     y: int,
                     width: Optional[int],
                     color: Optional[int],
                     outline: Optional[int]):
        self._painter.ellipse((x, y), fill=color, outline=outline, width=width)

    @public
    def draw_line(self,
                  x: int,
                  y: int,
                  color: Optional[int],
                  width: Optional[int],
                  rounded: bool):
        self._painter.line((x, y), fill=color, width=width, joint='curve' if rounded else None)

    @public
    def clear(self):
        self.fill(0, None)

    @public
    def write_file(self, filename: str):
        self._canvas.save(filename)

    @public
    def get_data(self):
        self._canvas.getdata()

    @public
    def reset_frame_count(self):
        self.LOG.info('frame counter reset')
        self._frame_count = 1
