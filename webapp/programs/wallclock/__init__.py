import time
import utils
from datetime import datetime as dt
from pluggram import Pluggram, Option


class WallClock(Pluggram):
    DISPLAY_NAME = 'Wall Clock'
    DESCRIPTION = 'Live digital clock display'
    VERSION = '1.0.0'
    TICK_RATE = '1s'
    OPTIONS = [
        Option('show_seconds', True),
        Option('flash_colon', True),
        Option('foreground', 0xFFFFFF, min=0, max=0xFFFFFF),
        Option('background', 0, min=0, max=0xFFFFFF),
        Option('font_size', 12, min=12, max=64)
    ]

    def __init__(self,
                 screen,
                 **options):
        self._show_seconds = options['show_seconds']
        self._flash_colon = options['flash_colon']
        self._foreground = options['foreground']
        self._background = options['background']
        self._size = options['font_size']
        self._screen = screen
        self._flasher = False
        self._text_width = None

        screen.fill(self._background)

    def render(self):
        # format time
        message = dt.now().strftime(f'%I{(":" if self._flasher else " ")}%M{("%S" if self._show_seconds else "")}%p')

        # get the text size
        if self._text_width is None:
            self._text_width, _ = utils.text_dimensions(message, self._size, bold=True)

        # adjust the center to the text size
        i = self._screen.center_index - (self._text_width / 2)

        # draw the text to screen
        self._screen.draw_text(i, self._foreground, self._size, message, bold=True)

        # invert the colon
        self._flasher = not self._flasher

        time.sleep(1)
