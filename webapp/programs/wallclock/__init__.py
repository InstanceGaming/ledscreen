from datetime import datetime as dt

from api import Screen
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
        Option('font_size', 16, min=16, max=32)
    ]

    def __init__(self,
                 screen: Screen,
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

    def tick(self):
        # format time
        message = dt.now().strftime(f'%I{(":" if self._flasher else " ")}%M{("%S" if self._show_seconds else "")}%p')

        # get the text size
        if self._text_width is None:
            self._text_width, _ = self._screen.text_dimensions(message)

        # adjust the center to the text size
        c = self._screen.center - (self._text_width / 2)

        # draw the text to screen
        self._screen.draw_text((c, self._screen.height / 2),
                               self._foreground,
                               message,
                               anchor='lt',
                               spacing=5,
                               alignment='center')

        # invert the colon
        self._flasher = not self._flasher
