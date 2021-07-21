from datetime import datetime as dt
from pluggram import Option

__pluggram__ = {
    'display_name': 'Wall Clock',
    'description': 'Live digital clock display',
    'version': '1.0.0',
    'entrypoint': None,
    'options': [
        Option('show_seconds', True),
        Option('flash_colon', True),
        Option('foreground', 0xFFFFFF),
        Option('background', 0)
    ]
}

OPTIONS = {}
SCREEN = None
FLASHER = True


def run(options, screen):
    global OPTIONS, SCREEN
    OPTIONS = options
    SCREEN = screen
    screen.fill(OPTIONS['background'])


def tick():
    global FLASHER
    message = dt.now().strftime(f'%I{(":" if FLASHER else " ")}%M{("%S" if OPTIONS["show_seconds"] else "")}%p')
    SCREEN.draw_text(SCREEN.center_index, OPTIONS['foreground'], 12, message, bold=True)
    FLASHER = not FLASHER
