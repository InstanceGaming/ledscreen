import api

config = {}
loaded_pluggrams = []
screen = None
running_pluggrams = []


def init(conf):
    global screen
    screen = api.Screen(
        conf['screen.width'],
        conf['screen.height'],
        conf['screen.gpio_pin'],
        conf['screen.frequency'],
        conf['screen.dma_channel'],
        conf['screen.brightness'],
        conf['screen.inverted'],
        conf['screen.gpio_channel'],
        conf['screen.fonts_dir']
    )


LOGIN_PAGE = 'auth.login'
LOGIN_TEMPLATE = 'pages/login.html'
MANAGEMENT_PAGE = 'manage.index'
MANAGEMENT_TEMPLATE = 'pages/manage.html'
