from datetime import datetime as dt

from api import Screen
from pluggram import Pluggram, Option


class WallClock(Pluggram):
    DISPLAY_NAME = 'Wall Clock'
    DESCRIPTION = 'Live digital clock display'
    VERSION = '1.0.0'
    TICK_RATE = '1ms'
    OPTIONS = [
        Option('line_count', 1, min=1, max=2),
        Option('foreground', 0xFFFFFF, min=0, max=0xFFFFFF),
        Option('background', 0, min=0, max=0xFFFFFF)
    ]
    FONT = 'arial.ttf'
    HALF_FONT = 10
    TALL_FONT = 47

    def __init__(self,
                 screen: Screen,
                 **options):
        self._line_count = options['line_count']
        self._fg = options['foreground']
        self._bg = options['background']
        self._screen = screen
        self._message = 'Melvin was here.'
        self._message_width = self._screen.text_dimensions(self._message)[0]
        self._char_width = self._message_width / len(self._message)
        self._x = self._screen.width + (self._message_width * 2)

        self._screen.clear()
        self._screen.set_font(self.FONT, self.TALL_FONT)

    def tick(self):
        center = self._screen.center

        self._screen.fill(self._bg)
        self._screen.draw_text((self._x, center[1]),
                               self._fg,
                               self._message,
                               anchor='mm',
                               alignment='center')

        if self._x == -(self._screen.width + (self._message_width * 2)):
            self._x = self._screen.width
        else:
            self._x -= 1

        # update the screen
        self._screen.render()
