import logging
import os
import subprocess
import sys
import shutil
import pathlib
from sqlalchemy import text as sql_text
from database import session, conditional_context
from models import (User,
                    UserType,
                    Workspace,
                    RunTarget,
                    generate_workspace_token_safe,
                    generate_user_token_safe, Session, RunStatus, RunLog)


def create_user(user_type: UserType,
                user_name: str,
                expiry=None,
                password=None,
                lock=False,
                context_needed=True):
    uid = generate_user_token_safe()
    short_text = uid[:16]

    logging.debug(f'creating user {short_text}')

    with conditional_context(context_needed):
        if user_type != UserType.STUDENT:
            lock = False
            accounts_of_type = User.query.filter_by(type=user_type).count()

            if accounts_of_type > 0:
                logging.error(f'cannot create another {user_type.name.lower()} account')
                return None

        user = User(uid,
                    user_type,
                    user_name,
                    expiry=expiry,
                    password=password,
                    lock=lock)

        session.add(user)

    logging.info(f'created user {short_text}')
    return user


def remove_user(uid: str,
                purge=False):
    short_text = uid[:16]
    logging.debug(f'removing user {short_text}')
    user = User.query.get(uid)

    if user is not None:
        with session.begin():
            if purge:
                workspaces = Workspace.query.filter_by(owner=uid)

                for w in workspaces:
                    logging.debug(f'user had associated workspace {w.wid[:16]}')
                    remove_workspace(w.wid)

            session.remove(user)
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

    with session.begin():
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

        session.add(workspace)

        logging.debug(f'inserted workspace database record')
        logging.info(f'created workspace {short_text}')

    return workspace


def coerce_workspace(w):
    with session.begin():
        if isinstance(w, str):
            if len(w) != 32:
                raise ValueError('Invalid WID')
            workspace = Workspace.query.get(w)
        elif isinstance(w, Workspace):
            workspace = w
        else:
            raise TypeError('Must be a string or Workspace instance')
        return workspace


def save_workspace_code(w, code_text: str):
    workspace = coerce_workspace(w)

    # 1. Check if program is running, if it is, return false
    if workspace.run_status != RunStatus.IDLE:
        return False

    # 2. Save to file
    file_path = os.path.join(workspace.storage_path, workspace.py_file)

    with open(file_path, 'w') as pyf:
        pyf.write(code_text)

    logging.debug(f'updated entrypoint "{file_path}"')

    return True


def run_workspace(w):
    workspace = coerce_workspace(w)

    # 1. Ensure all filesystem paths still exist, return false if not
    # 2. Copy files from storage to run directory
    # 3. Check if it can run on the big screen or simulator
    # 4. If it can run on the screen, stop or pause pluggram, return false if another student program is running
    # 5. Create run log
    # 6. Start program with timeout (if set)


def stop_workspace(w, graceful: bool):
    workspace = coerce_workspace(w)

    # 1. Stop or kill process
    # 2. Copy files from run to storage
    # 3. Update workspace status
    # 4. Update run log


def remove_workspace(w):
    with session.begin():
        workspace = coerce_workspace(w)

        if workspace is not None:
            logging.debug(f'attempting to remove workspace {workspace.short_wid}')
            session.delete(workspace)
            shutil.rmtree(workspace.env_path, ignore_errors=True)
            logging.debug(f'removing workspace: deleted environment directory {workspace.short_wid}')
            shutil.rmtree(workspace.storage_path, ignore_errors=True)
            logging.debug(f'removing workspace: deleted storage directory {workspace.short_wid}')
            logging.info(f'removed workspace {workspace.short_wid}')
            return True
    return False


def user_count() -> int:
    return session.query(User).count()


def needs_setup() -> bool:
    count = user_count()

    if count == 0:
        return True
    elif count == 1:
        with session.begin():
            user = session.query(User).first()

            if user.type != UserType.ADMIN:
                return True
            else:
                # has the admin logged in at least once?
                has_logged_in = user.login_at is not None
                if not has_logged_in:
                    return False
    return False


def shutdown():
    # todo: show message on screen

    if os.name == 'posix':
        args = ['poweroff']
        logging.info(f'shutting down...')
        proc = subprocess.Popen(args)
        return_code = proc.wait(2)
        logging.debug(f'poweroff return-code {return_code}')
    else:
        raise NotImplementedError('Intentionally left unimplemented; this system is only used on Linux, developed on '
                                  'Windows.')


def restart():
    # todo: show message on screen

    if os.name == 'posix':
        args = ['reboot']
        logging.info(f'restarting...')
        proc = subprocess.Popen(args)
        return_code = proc.wait(2)
        logging.debug(f'reboot return-code {return_code}')
    else:
        raise NotImplementedError('Intentionally left unimplemented; this system is only used on Linux, developed on '
                                  'Windows.')


def execute_sql(s, statement: str):
    sql = sql_text(statement)
    return s.execute(sql)


def truncate_table(s, table_name: str, ignore_constraints=False):
    if ignore_constraints:
        execute_sql(s, 'SET FOREIGN_KEY_CHECKS=0')

    result = execute_sql(s, f'TRUNCATE TABLE {table_name}')

    if ignore_constraints:
        execute_sql(s, 'SET FOREIGN_KEY_CHECKS=1')

    return result


def reset(keep_user=None, archive_dir=None):
    logging.warning(f'--- BEGINNING RESET ---')

    if keep_user is not None:
        assert isinstance(keep_user, User)
        logging.debug(f'keeping account {keep_user.uid}')

    # 1. Open a new DB transaction
    with session.begin():
        workspaces = session.query(Workspace).all()

        # 2. Force stop all running screen programs
        for workspace in workspaces:
            if workspace.run_status != RunStatus.IDLE:
                stop_workspace(workspace, False)

        # 3. Make backup of student code
        if archive_dir is not None:
            import zipfile

            os.makedirs(archive_dir, exist_ok=True)
            for workspace in workspaces:
                storage_dir = workspace.storage_path

                if os.path.isdir(storage_dir):
                    storage_files = list(pathlib.Path(storage_dir).rglob('*.*'))

                    if len(storage_files) > 0:
                        archive_name = f'{workspace.wid}.zip'
                        archive_path = os.path.join(archive_dir, archive_name)
                        archive = zipfile.ZipFile(archive_path, 'w')

                        for storage_file in storage_files:
                            archive.write(storage_file, compress_type=zipfile.ZIP_DEFLATED)

                        archive.close()
                        logging.debug(f'archived workspace {workspace.short_wid} '
                                      f'({len(storage_files)} files to "{archive_name}")')
                    else:
                        logging.debug(f'workspace {workspace.short_wid} has no files to archive')
                else:
                    logging.warning(f'skipping archive of workspace {workspace.short_wid}: '
                                    'storage directory does not exist or is not a directory')
                    continue

        # 4. Purge all sessions
        truncate_table(session, Session.__tablename__)

        # 5. For each workspace, call remove_workspace()
        for workspace in workspaces:
            remove_workspace(workspace)

        # 6. Purge all run logs
        truncate_table(session, RunLog.__tablename__)

        # 7. Remove all users (except for keep_user, if given)
        if keep_user is None:
            truncate_table(session, User.__tablename__, ignore_constraints=True)
        else:
            users = session.query(User).all()

            for user in users:
                if user != keep_user:
                    session.delete(user)

    logging.warning(f'--- RESET COMPLETED ---')
