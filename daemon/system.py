import logging
import os
import subprocess
import sys
import shutil
import pathlib
from models import (User,
                    UserType,
                    Workspace,
                    RunTarget,
                    generate_workspace_token_safe,
                    generate_user_token_safe,
                    db)


def create_user(user_type: UserType,
                user_name: str,
                expiry=None,
                password=None,
                lock=False):
    uid = generate_user_token_safe()
    short_text = uid[:16]

    logging.debug(f'creating user {short_text}')

    if user_type != UserType.STUDENT:
        lock = False

    user = User(uid,
                user_type,
                user_name,
                expiry=expiry,
                password=password,
                lock=lock)

    db.session.add(user)
    db.session.commit()

    logging.info(f'created user {short_text}')
    return user


def remove_user(uid: str,
                purge=False):
    short_text = uid[:16]
    logging.debug(f'removing user {short_text}')
    user = User.query.get(uid)

    if user is not None:
        # sessions will be auto-removed by database constraint

        if purge:
            workspaces = Workspace.query.filter_by(owner=uid)

            for w in workspaces:
                logging.debug(f'user had associated workspace {w.wid[:16]}')
                remove_workspace(w.wid)

        db.session.remove(user)
        logging.info(f'removed user {short_text}')
        return True

    return False


def mk_virtual_env(path: str,
                   prompt: str):
    assert isinstance(prompt, str) and len(prompt) > 0
    assert isinstance(path, str) and len(path) > 1

    current_interpreter_path = sys.executable
    args = [
        'virtualenv',
        '-p',
        current_interpreter_path,
        '--download',
        '--no-periodic-update',
        '--no-vcs-ignore',
        '--activators',
        'batch,bash',
        '--reset-app-data',
        '--prompt',
        f'"({prompt}) "',
        path
    ]
    logging.debug(f'running "virtualenv {path}"...')
    proc = subprocess.Popen(args)
    return_code = proc.wait(10)
    logging.debug(f'virtualenv return-code {return_code}')

    return return_code


def get_virtualenv_bin(env_dir: str):
    if sys.platform == "win32":
        return os.path.join(env_dir, 'Scripts')
    return os.path.join(env_dir, 'bin')


def create_workspace(envs_dir: str,
                     storage_dir: str,
                     run_dir: str,
                     py_filename: str,
                     py_contents=None,
                     owner=None,
                     run_privilege=None,
                     max_runtime=None):
    wid = generate_workspace_token_safe()
    short_text = wid[:16]

    if not os.path.isdir(envs_dir):
        raise RuntimeError('Environments directory does not exist')

    if not os.path.isdir(storage_dir):
        raise RuntimeError('Storage directory does not exist')

    if not os.path.isdir(run_dir):
        raise RuntimeError('Run directory does not exist')

    if len(py_filename) < 1:
        raise ValueError('py_filename: filename too short')

    if run_privilege is not None and not isinstance(run_privilege, RunTarget):
        raise ValueError('run_privilege: must be a RunTarget enum')

    if max_runtime is not None and max_runtime < 1:
        raise ValueError('max_runtime: must be at least 1')

    logging.debug(f'creating workspace {short_text}')

    run_dir = os.path.abspath(run_dir)

    env_path = os.path.abspath(os.path.join(envs_dir, wid))
    logging.debug(f'environment will be at "{env_path}"')
    os.makedirs(env_path, exist_ok=True)

    venv_return_code = mk_virtual_env(env_path, short_text)

    if venv_return_code != 0:
        logging.error(f'failed to create virtual environment: return code {venv_return_code}')

    current_interpreter_name = pathlib.Path(sys.executable).name
    bin_path = get_virtualenv_bin(env_path)
    interpreter_path = os.path.abspath(os.path.join(bin_path, current_interpreter_name))
    logging.debug(f'interpreter will be at "{interpreter_path}"')

    storage_path = os.path.abspath(os.path.join(storage_dir, wid))
    logging.debug(f'storage will be at "{interpreter_path}"')
    os.makedirs(storage_path, exist_ok=True)

    entrypoint_path = os.path.join(storage_path, py_filename)
    logging.debug(f'entrypoint will be at "{entrypoint_path}"')

    if py_contents is not None:
        with open(entrypoint_path, 'w') as ef:
            ef.write(py_contents)
        logging.debug(f'created entrypoint with content')
    else:
        pathlib.Path(entrypoint_path).touch(exist_ok=True)
        logging.debug(f'created entrypoint')

    workspace = Workspace(wid,
                          env_path,
                          storage_path,
                          run_dir,
                          interpreter_path,
                          py_file=py_filename,
                          owner=owner,
                          run_privilege=run_privilege,
                          max_runtime=max_runtime)

    db.session.add(workspace)
    db.session.commit()

    logging.debug(f'inserted workspace database record')
    logging.info(f'created workspace {short_text}')

    return workspace


def remove_workspace(wid: str):
    if len(wid) == 32:
        short_text = wid[:16]
        logging.debug(f'attempting to remove workspace {short_text}')
        workspace = Workspace.query.get(wid)
        if workspace is not None:
            db.session.delete(workspace)
            shutil.rmtree(workspace.env_path, ignore_errors=True)
            logging.debug(f'removing workspace: deleted environment directory {short_text}')
            shutil.rmtree(workspace.storage_path, ignore_errors=True)
            logging.debug(f'removing workspace: deleted storage directory {short_text}')
            db.session.commit()
            logging.info(f'removed workspace {short_text}')
            return True
    return False
