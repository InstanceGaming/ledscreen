from workspaces import *
import os
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s][%(module)s:%(lineno)s]: %(message)s',
                    datefmt='%x %H:%M:%S')

ENVS_DIR = 'environments'
RUN_DIR = 'run'
INTERPRETER_FILE = 'python.exe'

if __name__ == '__main__':
    logging.info('making directories...')
    os.makedirs(ENVS_DIR, exist_ok=True)
    os.makedirs(RUN_DIR, exist_ok=True)

    logging.info('starting workspace manager...')
    manager = WorkspaceManager(ENVS_DIR,
                               1001,
                               1010,
                               RUN_DIR,
                               INTERPRETER_FILE)
    logging.info('creating workspace...')
    workspace = manager.create()
    logging.info(f'created workspace "{workspace.short_wid}"')
    logging.info(f'running workspace "{workspace.short_wid}"...')
    workspace.run(True)
