import logging

LOG = logging.getLogger('ledscreen.api')

try:
    import rpi_ws281x
    _LED_STRIP_CLASS = rpi_ws281x.PixelStrip
except ModuleNotFoundError:
    from dummy_ws281x import DummyStrip
    _LED_STRIP_CLASS = DummyStrip


class Screen:

    @property
    def width(self):
        """
        Horizontal pixel count.
        """
        return self._w

    @property
    def height(self):
        """
        Vertical pixel count.
        """
        return self._h

    @property
    def pixel_count(self):
        """
        Get the screen area in pixels.
        """
        return self._w * self._h

    @property
    def center_index(self):
        raise NotImplementedError()

    @property
    def global_brightness(self):
        return self._global_brightness

    @global_brightness.setter
    def global_brightness(self, v: int):
        if v > 255 or v < 0:
            raise ValueError('Brightness must be within range 0-255')

        self._global_brightness = v
        self._pixel_strip.setBrightness(self._global_brightness)
        LOG.debug('global screen brightness changed ({})'.format(v))

    def __init__(self, w: int, h: int, output_pin: int, frequency: int, dma_channel: int, global_brightness: int,
                 invert_signal: bool, gpio_channel: int):
        super().__init__()
        self._logger = logging.getLogger()
        self._w = w
        self._h = h
        self._output_pin = output_pin
        self._global_brightness = global_brightness
        self._pixel_strip = _LED_STRIP_CLASS(self.pixel_count,
                                             self._output_pin,
                                             frequency,
                                             dma_channel,
                                             invert_signal,
                                             self._global_brightness,
                                             gpio_channel)
        self._pixel_strip.begin()

    def render(self):
        self._pixel_strip.show()

    def set_pixel(self, index, color: int):
        self._pixel_strip.setPixelColor(index, color)

    def draw_text(self,
                  index: int,
                  color: int,
                  size: int,
                  message: str,
                  bold=False):
        # todo: mind-bending text graphics
        raise NotImplementedError()

    def fill(self, color: int, animated=False):
        for i in range(self.pixel_count):
            self.set_pixel(i, color)

            if animated:
                self.render()

        if not animated:
            self.render()

    def clear(self, animated=False):
        self.fill(0, animated=animated)
