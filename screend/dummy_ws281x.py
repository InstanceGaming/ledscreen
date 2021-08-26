import logging


LOG = logging.getLogger('ledscreen.dummy_ws281x')


class DummyStrip:

    def __init__(self,
                 num,
                 pin,
                 freq_hz=800000,
                 dma=10,
                 invert=False,
                 brightness=255,
                 channel=0,
                 strip_type=None,
                 gamma=None):
        LOG.debug(f'DummyStrip({num}, {pin}, {freq_hz}, {dma}, {invert}, {brightness}, {channel}, {strip_type}, {gamma}) created')

    def begin(self):
        LOG.debug('begin() called')
        pass

    def show(self):
        LOG.debug('show() called')
        pass

    def setPixelColor(self, n, color):
        LOG.debug(f'setPixelColor({n}, {color}) called')
        pass

    def setPixelColorRGB(self, n, red, green, blue, white=0):
        LOG.debug(f'setPixelColorRGB({n}, {red}, {green}, {blue}, {white}) called')
        pass

    def setBrightness(self, brightness):
        LOG.debug(f'setBrightness({brightness}) called')
        pass

    def getPixelColor(self, n):
        LOG.debug(f'getPixelColor({n}) called')
        pass

    def getPixelColorRGB(self, n):
        LOG.debug(f'getPixelColorRGB({n}) called')
        pass

    def getPixelColorRGBW(self, n):
        LOG.debug(f'getPixelColorRGBW({n}) called')
        pass
