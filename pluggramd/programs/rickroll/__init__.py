import os
from PIL import Image
from rpc import Screen
from pluggram import Option, Pluggram


class Rickroll(Pluggram):
    DISPLAY_NAME = 'A Classic'
    DESCRIPTION = 'Plays GIF of an internet classic'
    VERSION = '1.0.0'
    TICK_RATE = '100ms'
    OPTIONS = [
        Option('brightness', 128, min=1, max=190)
    ]
    FILE = 'media/rick.gif'

    def __init__(self,
                 screen: Screen,
                 **options):
        self._screen = screen

        if not os.path.exists(self.FILE):
            raise FileNotFoundError(f'Rick Astley not found')

        self._gif = Image.open(self.FILE)
        self._frame_count = self._gif.n_frames
        self._frame_index = 0

        self._screen.clear()
        self._screen.set_brightness(options['brightness'])

    def tick(self):
        self._gif.seek(self._frame_index)
        self._screen.paste(self._gif)

        # update the screen
        self._screen.render()

        self._frame_index += 1
        if self._frame_index >= self._frame_count:
            self._frame_index = 0
