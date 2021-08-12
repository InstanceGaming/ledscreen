from datetime import datetime as dt

from api import Screen, MAX_BRIGHTNESS
from pluggram import Pluggram, Option


class WallClock(Pluggram):
    DISPLAY_NAME = 'Wall Clock'
    DESCRIPTION = 'Live digital clock display'
    VERSION = '1.0.0'
    TICK_RATE = '500ms'
    OPTIONS = [
        Option('brightness', 128, min=1, max=MAX_BRIGHTNESS),
        Option('foreground', 0xFFFFFF, min=0, max=0xFFFFFF, color_picker=True, help='Color of all rendered text.'),
        Option('background', 0, min=0, max=0xFFFFFF, color_picker=True, help='Color behind text.'),
        Option('stroke_thickness', 0, min=0, max=10, help='Number of pixels to outline around time text.'),
        Option('stroke_color', 0, min=0, max=0xFFFFFF, color_picker=True, help='Color of outline around time text.'),
        Option('show_seconds', True, help='Show seconds next to minutes counter.'),
        Option('flash_colon', True, help='Either maintain a static colon symbol or flash it every second.'),
        Option('show_date', False, help='Show current date above time.')
    ]
    FONT_REG = 'arial.ttf'
    FONT_BOLD = 'arialbd.ttf'
    SMALL_FONT = 10
    LARGE_FONT = 12

    def __init__(self,
                 screen: Screen,
                 **options):
        self._brightness = options['brightness']
        self._show_seconds = options['show_seconds']
        self._flash_colon = options['flash_colon']
        self._foreground = options['foreground']
        self._background = options['background']
        self._show_date = options['show_date']
        self._stroke_thickness = options['stroke_thickness']
        self._stroke_fill = options['stroke_color']
        self._screen = screen
        self._flasher = True
        self._text_width = None

        self._screen.clear()
        self._screen.set_brightness(self._brightness)

        if not self._show_date:
            self._screen.set_font(self.FONT_BOLD, size=self.LARGE_FONT)

    def tick(self):
        now = dt.now()
        self._screen.fill(self._background)

        # format time
        colon = (":" if self._flasher else " ")
        second_text = f'{colon}%S' if self._show_seconds else ""
        date_text = now.strftime('%a\n%b %m')
        time_text = now.strftime(f'%I{colon}%M{second_text}')

        center = self._screen.center

        if self._show_date:
            # date
            self._screen.set_font(self.FONT_REG, size=self.SMALL_FONT)
            self._screen.draw_text((center[0], 0),
                                   self._foreground,
                                   date_text,
                                   anchor='ma',
                                   spacing=0,
                                   alignment='center')
            self._screen.set_font(self.FONT_BOLD, size=self.LARGE_FONT)

        # time
        time_pos = (center[0], self._screen.height - 2) if self._show_date else center
        self._screen.draw_text(time_pos,
                               self._foreground,
                               time_text,
                               anchor='mb' if self._show_date else 'mm',
                               alignment='center',
                               stroke_width=self._stroke_thickness,
                               stroke_fill=self._stroke_fill)

        # update the screen
        self._screen.render()

        # invert the colon
        if self._flash_colon:
            self._flasher = not self._flasher
