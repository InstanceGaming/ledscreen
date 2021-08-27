from datetime import datetime, timedelta
import utils
from pluggram import Pluggram, Option
from rpc import Screen


class BackSoon(Pluggram):
    DISPLAY_NAME = 'Back Soon'
    DESCRIPTION = 'Dynamic "I\'ll be back in X" message'
    VERSION = '1.0.0'
    TICK_RATE = '500ms'
    OPTIONS = [
        Option('brightness', 128, min=1, max=190),
        Option('minutes', 5, min=1),
        Option('foreground', 0xFFFFFF, min=0, max=0xFFFFFF, color_picker=True),
        Option('background', 0, min=0, max=0xFFFFFF, color_picker=True)
    ]
    FONT = 'slkscr.ttf'

    def __init__(self,
                 screen: Screen,
                 **options):
        self._brightness = options['brightness']
        self._foreground = options['foreground']
        self._background = options['background']
        self._minutes = options['minutes']
        self._start = datetime.now()
        self._posted_text = self._start.strftime('%I:%M%p')
        self._end = datetime.now() + timedelta(minutes=self._minutes)
        self._screen = screen
        self._flasher = True

        self._screen.clear()
        self._screen.set_brightness(self._brightness)

    def tick(self):
        self._screen.fill(self._background)

        center = self._screen.center

        self._screen.set_font(self.FONT, 8)
        self._screen.draw_text(center[0],
                               3,
                               self._foreground,
                               'WILL BE',
                               anchor='mm',
                               alignment='center')
        self._screen.draw_text(center[0],
                               9,
                               self._foreground,
                               'BACK IN',
                               anchor='mm',
                               alignment='center')
        if self._flasher:
            duration = self._end - datetime.now()

            if duration.total_seconds() > 0:
                duration_text = utils.pretty_timedelta(duration, format_spec='.0f')
            else:
                duration_text = 'UNKNOWN'

            self._screen.set_font(self.FONT, 9)
            self._screen.draw_text(center[0],
                                   18,
                                   0x00ffff,
                                   duration_text.upper(),
                                   anchor='mm',
                                   alignment='center')

        self._screen.set_font(self.FONT, 8)
        self._screen.draw_text(center[0],
                               25,
                               self._foreground,
                               'POSTED',
                               anchor='mm',
                               alignment='center')
        if self._flasher:
            self._screen.set_font(self.FONT, 9)
            self._screen.draw_text(center[0],
                                   33,
                                   0x0000ff,
                                   self._posted_text,
                                   anchor='mm',
                                   alignment='center')

        # update the screen
        self._screen.render()

        self._flasher = not self._flasher
