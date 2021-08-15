import os
from utils import timing_counter
from api import Screen
from pluggram import load
import traceback
import argparse


def get_cla():
    ap = argparse.ArgumentParser(description='Testing ground for pluggrams')
    ap.add_argument('-f',
                    type=str,
                    metavar='DIRECTORY',
                    dest='frames_dir',
                    default=None,
                    help='Directory to create frame images in.')
    ap.add_argument('-e',
                    type=int,
                    metavar='COUNT',
                    dest='end_frame',
                    default=0,
                    help='Stop program after drawing this many frames.')
    ap.add_argument('-p',
                    type=str,
                    metavar='DIRECTORY',
                    dest='programs_dir',
                    default='programs',
                    help='Location of pluggram modules.')
    ap.add_argument(type=str,
                    metavar='MODULE_NAME',
                    dest='module_name',
                    help='Name of a pluggram module to load within the configured programs directory.')
    return ap.parse_args()


if __name__ == '__main__':
    screen = Screen(54,
                    36,
                    18,
                    800000,
                    10,
                    128,
                    False,
                    0,
                    'fonts')

    cla = get_cla()

    module_name = cla.module_name
    frames_dir = cla.frames_dir if cla.frames_dir is not None else None
    end_frame = cla.end_frame

    if frames_dir is not None:
        if not os.path.isdir(frames_dir):
            print('Frame output path does not exist or is not a directory')
            exit(2)

    loaded_pluggrams = load('programs', 1)
    print(f'loaded {len(loaded_pluggrams)} pluggrams')

    if len(loaded_pluggrams) > 0:
        pgm = None
        selection_name = module_name.lower().strip()
        for pg in loaded_pluggrams:
            if pg.name == selection_name:
                pgm = pg
                break
        else:
            print(f'"{selection_name}" not found')
            exit(11)

        print(f'selected "{pgm.name}"')

        if pgm.has_user_options:
            try:
                pgm.load_options()
            except OSError as e:
                print(f'error occurred loading user options: {str(e)}')
                exit(12)

            print(f'loaded user preferences')

        try:
            pgm.init(screen)
        except Exception as e:
            print(f'exception {e.__class__.__name__} initializing pluggram "{pgm.name}" ({pgm.class_name}): {str(e)}')
            print(traceback.format_exc())
            exit(100)

        output_dir = 'frames'
        frame_count = 1
        rate = pgm.tick_rate
        marker = -rate if rate is not None else timing_counter()
        try:
            while True:
                if (rate is not None and timing_counter() - marker > rate) or rate is None:
                    marker = timing_counter()
                    try:
                        pgm.tick()
                    except Exception as e:
                        print(f'exception {e.__class__.__name__} updating pluggram "{pgm.name}": {str(e)}')
                        print(traceback.format_exc())
                        exit(101)

                    if frames_dir is not None:
                        filename = f'{frame_count}.png'
                        path = os.path.join(output_dir, filename)
                        screen.write_file(path)

                    print(f'frame #{frame_count}')
                    frame_count += 1

                    if end_frame > 0:
                        if frame_count > end_frame:
                            break
        except KeyboardInterrupt:
            print('interrupted')
            exit(0)
else:
    print('This script must be ran directly.')
    exit(1)
