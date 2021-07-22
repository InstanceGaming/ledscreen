from datetime import datetime as dt
from pluggram import Pluggram, Option


class WallClock(Pluggram):
    DISPLAY_NAME = 'Wall Clock'
    DESCRIPTION = 'Live digital clock display'
    VERSION = '1.0.0'
    OPTIONS = [
        Option('show_seconds', True),
        Option('flash_colon', True),
        Option('foreground', 0xFFFFFF, min=0, max=0xFFFFFF),
        Option('background', 0, min=0, max=0xFFFFFF),
        Option('font_size', 12, min=12, max=64)
    ]

    def __init__(self,
                 screen,
                 **kwargs):
        self._show_seconds = kwargs['show_seconds']
        self._flash_colon = kwargs['flash_colon']
        self._foreground = kwargs['foreground']
        self._background = kwargs['background']
        self._size = kwargs['font_size']
        self._screen = screen
        self._flasher = False

        screen.fill(self._background)

    def render(self):
        message = dt.now().strftime(f'%I{(":" if self._flasher else " ")}%M{("%S" if self._show_seconds else "")}%p')
        self._screen.draw_text(self._screen.center_index, self._foreground, self._size, message, bold=True)
        self._flasher = not self._flasher
