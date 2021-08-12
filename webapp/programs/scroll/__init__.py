from api import Screen, MAX_BRIGHTNESS
from pluggram import Pluggram, Option
from utils import timing_counter


class ScrollingText(Pluggram):
    DISPLAY_NAME = 'Scrolling Text'
    DESCRIPTION = 'Live text scroller'
    VERSION = '1.0.0'
    TICK_RATE = '10ms'
    OPTIONS = [
        Option('brightness', 128, min=1, max=MAX_BRIGHTNESS),
        Option('line_count', 1, min=1, max=2),
        Option('start_delay', 1000),
        Option('foreground', 0x0000FF, min=0, max=0xFFFFFF, color_picker=True),
        Option('background', 0, min=0, max=0xFFFFFF, color_picker=True)
    ]
    FONT = 'slkscrb.ttf'
    HALF_FONT = 10
    TALL_FONT = 47

    def __init__(self,
                 screen: Screen,
                 **options):
        self._brightness = options['brightness']
        self._line_count = options['line_count']
        self._fg = options['foreground']
        self._bg = options['background']
        self._delay_ms = options['start_delay']
        self._screen = screen
        self._message = 'Hello world.'
        self._message_width = self._screen.text_dimensions(self._message)[0]
        self._char_width = self._message_width / len(self._message)
        self._reset_pos = self._screen.width + self._message_width
        self._scrolling_enabled = False
        self._x = 0

        self._screen.clear()
        self._screen.set_brightness(self._brightness)
        self._screen.set_font(self.FONT, 10)

        self.draw_line_message()
        self._screen.render()

        self._start_marker = timing_counter()
        print(f'start {self._start_marker}')

    def draw_line_message(self):
        self._screen.fill(self._bg)
        self._screen.draw_text((self._x, 0),
                               self._fg,
                               self._message,
                               anchor='lt',
                               alignment='left')

    def tick(self):
        if self._scrolling_enabled:
            self.draw_line_message()

            if self._x == -self._reset_pos:
                self._x = self._reset_pos
            else:
                self._x -= 1

            self._screen.render()
        else:
            print(f'start {timing_counter()}')
            if timing_counter() - self._start_marker > self._delay_ms:
                self._scrolling_enabled = True
