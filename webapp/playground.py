import os

from utils import timing_counter, pretty_ms
from api import Screen
from pluggram import load
import traceback


def benchmark(name: str, m):
    delta = timing_counter() - m
    print(f'{name} took {pretty_ms(delta)}')


screen = Screen(54,
                36,
                18,
                800000,
                10,
                128,
                False,
                0,
                'fonts')

pgm = load('programs', 1)
print(f'loaded {len(pgm)} pluggrams')

if len(pgm) > 0:
    active_pluggram = pgm[0]

    try:
        active_pluggram.init(screen, foreground=0x00FF00)
    except Exception as e:
        print(f'exception {e.__class__.__name__} initializing pluggram "{active_pluggram.name}" ({active_pluggram.class_name}): {str(e)}')
        print(traceback.format_exc())
        exit(100)

    output_dir = 'frames'
    frame_count = 1
    marker = timing_counter()
    try:
        while True:
            if timing_counter() - marker > active_pluggram.tick_rate:
                marker = timing_counter()
                try:
                    active_pluggram.tick()
                except Exception as e:
                    print(f'exception {e.__class__.__name__} updating pluggram "{active_pluggram.name}": {str(e)}')
                    print(traceback.format_exc())
                    exit(101)
                filename = f'{frame_count}.png'
                path = os.path.join(output_dir, filename)
                screen.write_file(path)
                print(f'frame #{frame_count}')
                frame_count += 1

                if frame_count > 420:
                    break
    except KeyboardInterrupt:
        print('interrupted')
        exit(0)
