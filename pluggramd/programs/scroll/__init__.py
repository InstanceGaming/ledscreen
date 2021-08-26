import utils
from pluggram import Pluggram, Option
from rpc import Screen
from utils import timing_counter
import random


class ScrollingText(Pluggram):
    DISPLAY_NAME = 'Scroll'
    DESCRIPTION = 'Scrolling text message board'
    VERSION = '1.0.0'
    TICK_RATE = '20ms'
    OPTIONS = [
        Option('brightness', 128, min=1, max=190),
        Option('message', 'Computer science rocks!', min=1),
        Option('font', 'slkscr.ttf', min=5,
               help='What TrueType font face to load from file. (.ttf)'),
        Option('start_delay', 1000, min=0, help='Wait this many milliseconds before scrolling.'),
        Option('font_size', 17, min=6, max=60),
        Option('frame_skip', 1, min=1, max=100, help='How many frames to skip per tick.'),
        Option('foreground', 0xFFFFFF, min=0, max=0xFFFFFF, color_picker=True, help='Text color.'),
        Option('background', 0, min=0, max=0xFFFFFF, color_picker=True),
        Option('stroke_thickness', 0, min=0, max=10, help='Number of pixels to outline around text.'),
        Option('stroke_color', 0, min=0, max=0xFFFFFF, color_picker=True, help='Color of outline around text.'),
        Option('centered', True),
        Option('randomize', True, help='Randomize text color after each cycle.'),
        Option('extra_space', True, help='Some fonts report false width calculations, '
                                         'this helps compensate for it when enabled.'),
    ]

    def __init__(self,
                 screen: Screen,
                 **options):
        self._brightness = options['brightness']
        self._fg = options['foreground']
        self._bg = options['background']
        self._centered = options['centered']
        self._randomize = options['randomize']
        self._extra_space = options['extra_space']
        self._stroke_thickness = options['stroke_thickness']
        self._stroke_color = options['stroke_color']
        self._delay_ms = options['start_delay']
        self._font_size = options['font_size']
        self._frame_skip = options['frame_skip']
        self._font = options['font']
        self._screen = screen
        self._message = options['message']
        self._size = self._screen.text_dimensions(self._message)
        self._reset_pos = self._size[0] + (self._screen.width * (2 if self._extra_space else 1))
        self._scrolling_enabled = False
        self._x = 0

        self._screen.clear()
        self._screen.set_brightness(self._brightness)
        self._screen.set_font(self._font, self._font_size)

        self.draw_line_message()
        self._screen.render()

        self._start_marker = timing_counter()

    def draw_line_message(self):
        self._screen.fill(self._bg)
        if self._centered:
            self._screen.draw_text((self._x, (self._screen.height / 2)),
                                   self._fg,
                                   self._message,
                                   anchor='lm',
                                   alignment='left',
                                   stroke_width=self._stroke_thickness,
                                   stroke_fill=self._stroke_color)
        else:
            self._screen.draw_text((self._x, 0),
                                   self._fg,
                                   self._message,
                                   anchor='lt',
                                   alignment='left',
                                   stroke_width=self._stroke_thickness,
                                   stroke_fill=self._stroke_color)

    def tick(self):
        if self._scrolling_enabled:
            self.draw_line_message()

            if self._x == -self._reset_pos:
                self._x = self._screen.width

                if self._randomize:
                    self._fg = utils.combine_rgb(
                        random.randrange(0x11, 0xFF),
                        random.randrange(0x11, 0xFF),
                        random.randrange(0x11, 0xFF)
                    )
            else:
                self._x -= self._frame_skip

            self._screen.render()
        else:
            if timing_counter() - self._start_marker > self._delay_ms:
                self._scrolling_enabled = True
