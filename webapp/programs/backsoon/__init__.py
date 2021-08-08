from datetime import datetime as dt

from api import Screen
from pluggram import Pluggram, Option


class WallClock(Pluggram):
    DISPLAY_NAME = 'Back Soon'
    DESCRIPTION = 'Dynamic "I\'ll be back in X" message'
    VERSION = '1.0.0'
    TICK_RATE = '500ms'
    OPTIONS = [
        Option('foreground', 0xFFFFFF, min=0, max=0xFFFFFF),
        Option('background', 0, min=0, max=0xFFFFFF)
    ]
    FONT = 'slkscr.ttf'
    BOLD_FONT = 'slkscrb.ttf'

    def __init__(self,
                 screen: Screen,
                 **options):
        self._foreground = options['foreground']
        self._background = options['background']
        self._screen = screen
        self._flasher = True

    def tick(self):
        self._screen.fill(self._background)

        center = self._screen.center

        self._screen.set_font(self.FONT, 8)
        self._screen.draw_text((center[0], 3),
                               self._foreground,
                               'WILL BE',
                               anchor='mm',
                               alignment='center')
        self._screen.draw_text((center[0], 9),
                               self._foreground,
                               'BACK IN',
                               anchor='mm',
                               alignment='center')
        if self._flasher:
            self._screen.set_font(self.BOLD_FONT, 10)
            self._screen.draw_text((center[0], 18),
                                   0x00ffff,
                                   '1 HOUR',
                                   anchor='mm',
                                   alignment='center')
        self._screen.set_font(self.FONT, 8)
        self._screen.draw_text((center[0], 26),
                               self._foreground,
                               'POSTED',
                               anchor='mm',
                               alignment='center')
        if self._flasher:
            self._screen.set_font(self.FONT, 9)
            self._screen.draw_text((center[0], 33),
                                   0x0000ff,
                                   '9:32am',
                                   anchor='mm',
                                   alignment='center')

        # update the screen
        self._screen.render()

        self._flasher = not self._flasher
