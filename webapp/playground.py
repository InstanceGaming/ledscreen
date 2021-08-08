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
    selected_pluggram_meta = pgm[0]
    print(f'selected "{selected_pluggram_meta.name}"')

    try:
        pluggram_instance = selected_pluggram_meta.init(screen)
    except Exception as e:
        print(f'exception {e.__class__.__name__} initializing pluggram "{selected_pluggram_meta.name}" ({selected_pluggram_meta.class_name}): {str(e)}')
        print(traceback.format_exc())
        exit(100)

    output_dir = 'frames'
    frame_count = 1
    rate = selected_pluggram_meta.tick_rate
    marker = -rate
    try:
        while True:
            if (rate is not None and timing_counter() - marker > rate) or rate is None:
                marker = timing_counter()
                try:
                    pluggram_instance.tick()
                except Exception as e:
                    print(f'exception {e.__class__.__name__} updating pluggram "{selected_pluggram_meta.name}": {str(e)}')
                    print(traceback.format_exc())
                    exit(101)
                filename = f'{frame_count}.png'
                path = os.path.join(output_dir, filename)
                screen.write_file(path)
                print(f'frame #{frame_count}')
                frame_count += 1

                if frame_count == 2:
                    break
    except KeyboardInterrupt:
        print('interrupted')
        exit(0)
