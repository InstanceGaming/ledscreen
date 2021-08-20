import os
from PIL import Image
from api import Screen, MAX_BRIGHTNESS
from pluggram import Pluggram, Option


class Rickroll(Pluggram):
    DISPLAY_NAME = 'A Classic'
    DESCRIPTION = 'Plays GIF of an internet classic'
    VERSION = '1.0.0'
    TICK_RATE = None
    OPTIONS = [
        Option('brightness', 128, min=1, max=MAX_BRIGHTNESS)
    ]
    FILE_PATH = 'static/images/rick.gif'

    def __init__(self,
                 screen: Screen,
                 **options):
        self._screen = screen

        if not os.path.exists(self.FILE_PATH):
            raise FileNotFoundError('Rick Astley not Found')

        self._gif = Image.open(self.FILE_PATH)
        self._frame_count = self._gif.n_frames
        self._frame_index = 0

        self._screen.clear()
        self._screen.set_brightness(options['brightness'])

    def tick(self):
        self._gif.seek(self._frame_index)
        self._screen.swap_frame(self._gif)

        # update the screen
        self._screen.render()

        self._frame_index += 1
        if self._frame_index >= self._frame_count:
            self._frame_index = 0
