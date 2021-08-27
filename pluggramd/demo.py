import os
import api
import zmq
import json
import argparse
import traceback
from utils import timing_counter
from tinyrpc import RPCClient
from pluggram import load
from tinyrpc.transports.zmq import ZmqClientTransport
from tinyrpc.protocols.msgpackrpc import MSGPACKRPCProtocol


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
                    help='Location of pluggram modules. Default is "programs"')
    ap.add_argument(type=str,
                    metavar='MODULE_NAME',
                    dest='module_name',
                    help='Name of a pluggram module to load within the '
                         'configured programs directory.')
    ap.add_argument(type=str,
                    metavar='URL',
                    dest='rpc_url',
                    help='RPC screen server URL.')
    return ap.parse_args()


if __name__ == '__main__':
    cla = get_cla()

    module_name = cla.module_name
    rpc_url = cla.rpc_url
    frames_dir = cla.frames_dir if cla.frames_dir is not None else None
    end_frame = cla.end_frame

    context = zmq.Context()
    client = RPCClient(
        MSGPACKRPCProtocol(),
        ZmqClientTransport.create(context, rpc_url)
    )

    proxy_obj = client.get_proxy()
    screen = api.Screen(proxy_obj)

    if frames_dir is not None:
        if not os.path.isdir(frames_dir):
            print('Frame output path does not exist or is not a directory')
            exit(2)

    metas, klass_objects = load('programs', 1)
    print(f'loaded {len(metas)} pluggrams')

    if len(metas) > 0:
        pgm = None
        pgc = None
        selection_name = module_name.lower().strip()
        for pg, pc in zip(metas, klass_objects):
            if pg.name == selection_name:
                pgm = pg
                pgc = pc
                break
        else:
            print(f'"{selection_name}" not found or was disqualified')
            exit(11)

        print(f'selected "{pgm.name}"')

        if pgm.has_user_options:
            try:
                pgm.load_options()
            except OSError as e:
                print(f'error occurred loading user options: {str(e)}')
                exit(12)
            except json.JSONDecodeError as e:
                print(f'could not parse user options JSON: {str(e)}')

            print(f'loaded user preferences')

        try:
            instance = pgm.init(pgc, screen)
        except Exception as e:
            print(f'exception {e.__class__.__name__} initializing pluggram '
                  f'"{pgm.name}" ({pgm.class_name}): {str(e)}')
            print(traceback.format_exc())
            exit(100)

        output_dir = 'frames'
        frame_count = 1
        rate = pgm.tick_rate
        marker = -rate if rate is not None else timing_counter()
        try:
            while True:
                if (rate is not None and timing_counter() - marker > rate) or \
                        rate is None:
                    marker = timing_counter()
                    try:
                        instance.tick()
                    except Exception as e:
                        print(f'exception {e.__class__.__name__} updating '
                              f'pluggram "{pgm.name}": {str(e)}')
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
