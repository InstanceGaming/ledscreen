import logging


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
        logging.debug(f'DummyStrip({num}, {pin}, {freq_hz}, {dma}, {invert}, {brightness}, {channel}, {strip_type}, {gamma}) created')

    def begin(self):
        logging.debug('begin() called')

    def show(self):
        logging.debug('show() called')

    def setPixelColor(self, n, color):
        logging.debug(f'setPixelColor({n}, {color}) called')

    def setPixelColorRGB(self, n, red, green, blue, white=0):
        logging.debug(f'setPixelColorRGB({n}, {red}, {green}, {blue}, {white}) called')

    def setBrightness(self, brightness):
        logging.debug(f'setBrightness({brightness}) called')

    def getPixelColor(self, n):
        logging.debug(f'getPixelColor({n}) called')

    def getPixelColorRGB(self, n):
        logging.debug(f'getPixelColorRGB({n}) called')

    def getPixelColorRGBW(self, n):
        logging.debug(f'getPixelColorRGBW({n}) called')
