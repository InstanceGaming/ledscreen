from rpc import Screen
from datetime import datetime, timedelta
from pluggram import Option, Pluggram


def better_timedelta_format(td):
    total_seconds = td.total_seconds()
    hours = total_seconds // 3600
    # remaining seconds
    s = total_seconds - (hours * 3600)
    # minutes
    minutes = s // 60
    # remaining seconds
    seconds = s - (minutes * 60)
    # total time
    return '{:02}:{:02}'.format(int(minutes), int(seconds))


class Timer(Pluggram):
    DISPLAY_NAME = 'Timer'
    DESCRIPTION = 'Live countdown timer'
    VERSION = '1.0.0'
    TICK_RATE = '100ms'
    OPTIONS = [
        Option('brightness', 128, min=1, max=190),
        Option('minutes', 5, min=0.125,
               help='How many minutes the timer will last.'),
        Option('foreground', 0xFFFFFF, min=0, max=0xFFFFFF, color_picker=True,
               help='Color of all rendered text.'),
        Option('background', 0, min=0, max=0xFFFFFF, color_picker=True,
               help='Color behind text.'),
        Option('stroke_thickness', 0, min=0, max=10,
               help='Number of pixels to outline around time text.'),
        Option('stroke_color', 0, min=0, max=0xFFFFFF, color_picker=True,
               help='Color of outline around time text.')
    ]
    FONT = 'arialbd.ttf'
    FONT_SIZE = 19

    def __init__(self,
                 screen: Screen,
                 **options):
        self._brightness = options['brightness']
        self._minutes = options['minutes']
        self._foreground = options['foreground']
        self._background = options['background']
        self._stroke_thickness = options['stroke_thickness']
        self._stroke_fill = options['stroke_color']
        self._screen = screen

        self._screen.clear()
        self._screen.set_brightness(self._brightness)
        self._screen.set_font(self.FONT, self.FONT_SIZE)

        self._end = datetime.utcnow() + timedelta(minutes=self._minutes)

    def tick(self):
        now = datetime.utcnow()
        delta: timedelta = (self._end - now)

        if delta.total_seconds() > 1:
            message = better_timedelta_format(delta)
        else:
            message = '00:00'
            self._foreground = 0x0000FF

        self._screen.fill(self._background)

        center = self._screen.center
        self._screen.draw_text(center[0],
                               center[1],
                               self._foreground,
                               message,
                               anchor='mm',
                               alignment='center',
                               stroke_width=self._stroke_thickness,
                               stroke_fill=self._stroke_fill)

        # update the screen
        self._screen.render()
