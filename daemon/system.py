import json
import logging
import os
import signal
import subprocess
import sys
import shutil
import pathlib
import threading

from wheel.util import native

import utils
from datetime import datetime as dt
from typing import Callable, Union
from common import CONFIG
from distutils.errors import DistutilsError
from distutils.dir_util import copy_tree
from sqlalchemy import text as sql_text
from database import session, conditional_context
from models import (User,
                    UserType,
                    Workspace,
                    RunTarget,
                    generate_workspace_token_safe,
                    generate_user_token_safe, Session, RunStatus, RunLog, generate_run_log_token_safe, ExitReason)
from pluggram import PluggramMeta

VERSION = '1.0.0'
LOG = logging.getLogger('ledscreen.system')
ACTIVE_PLUGGRAM = None


def start_pluggram(pluggram: PluggramMeta) -> bool:
    pass


def pause_pluggram(pluggram: PluggramMeta, clear_screen=False):
    pass


def stop_pluggram(pluggram: PluggramMeta):
    pause_pluggram(pluggram, clear_screen=True)


def create_user(user_type: UserType,
                user_name: str,
                expiry=None,
                password=None,
                lock=False,
                context_needed=True):
    uid = generate_user_token_safe()
    short_text = uid[:16]

    LOG.debug(f'creating user {short_text}')

    with conditional_context(context_needed):
        if user_type != UserType.STUDENT:
            lock = False
            accounts_of_type = User.query.filter_by(type=user_type).count()

            if accounts_of_type > 0:
                LOG.error(f'cannot create another {user_type.name.lower()} account')
                return None

        user = User(uid,
                    user_type,
                    user_name,
                    expiry=expiry,
                    password=password,
                    lock=lock)

        session.add(user)

    LOG.info(f'created user {short_text}')
    return user


def remove_user(uid: str,
                purge=False):
    short_text = uid[:16]
    LOG.debug(f'removing user {short_text}')
    user = User.query.get(uid)

    if user is not None:
        if purge:
            with session.begin():
                workspaces = Workspace.query.filter_by(owner=uid)

            for w in workspaces:
                LOG.debug(f'user had associated workspace {w.wid[:16]}')
                remove_workspace(w.wid)

        with session.begin():
            session.delete(user)
        LOG.info(f'removed user {short_text}')
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
    LOG.debug(f'running "virtualenv {path}"...')
    proc = subprocess.Popen(args)
    return_code = proc.wait(10)
    LOG.debug(f'virtualenv return-code {return_code}')

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
        LOG.debug(f'creating workspace {short_text}')

        run_dir = os.path.abspath(run_dir)

        env_path = os.path.abspath(os.path.join(envs_dir, wid))
        LOG.debug(f'environment will be at "{env_path}"')
        os.makedirs(env_path, exist_ok=True)

        venv_return_code = mk_virtual_env(env_path, short_text)

        if venv_return_code != 0:
            LOG.error(f'failed to create virtual environment: return code {venv_return_code}')

        current_interpreter_name = pathlib.Path(sys.executable).name
        bin_path = get_virtualenv_bin(env_path)
        interpreter_path = os.path.abspath(os.path.join(bin_path, current_interpreter_name))
        LOG.debug(f'interpreter will be at "{interpreter_path}"')

        storage_path = os.path.abspath(os.path.join(storage_dir, wid))
        LOG.debug(f'storage will be at "{interpreter_path}"')
        os.makedirs(storage_path, exist_ok=True)

        entrypoint_path = os.path.join(storage_path, py_filename)
        LOG.debug(f'entrypoint will be at "{entrypoint_path}"')

        if py_contents is not None:
            with open(entrypoint_path, 'w') as ef:
                ef.write(py_contents)
            LOG.debug(f'created entrypoint with content')
        else:
            pathlib.Path(entrypoint_path).touch(exist_ok=True)
            LOG.debug(f'created entrypoint')

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

        LOG.debug(f'inserted workspace database record')
        LOG.info(f'created workspace {short_text}')

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

    LOG.debug(f'updated entrypoint "{file_path}"')

    return True


def create_run_log(pid: int, interpreter_path: str, run_path: str, workspace=None, user=None):
    rid = generate_run_log_token_safe()

    if workspace is not None:
        assert isinstance(workspace, str)

    if user is not None:
        assert isinstance(user, str)

    LOG.debug(f'attempting to create run log for "{run_path}" ({rid[:16]})')

    if not os.path.exists(run_path):
        raise RuntimeError('Cannot create run log for non-existent executable')

    if not os.path.exists(interpreter_path):
        raise RuntimeError('Cannot create run log with non-existent interpreter')

    with session.begin():
        run_log = RunLog(rid,
                         pid,
                         interpreter_path,
                         run_path,
                         user=user,
                         workspace=workspace)
        session.add(run_log)
        LOG.debug(f'created run log {run_log.short_rid}')
        return run_log


def complete_run_log(rid: str,
                     reason: ExitReason,
                     return_code,
                     std_out=None,
                     std_err=None,
                     datetime=None):
    with session.begin():
        log = RunLog.query.get(rid)

        if log is not None:
            log.return_code = return_code
            log.std_out = std_out
            log.std_error = std_err
            log.exit_reason = reason
            log.stopped_at = datetime or dt.utcnow()
            LOG.debug(f'completed run log {log.short_rid}')
        else:
            raise RuntimeError('Bad RID')


def clean_run_dir():
    run_dir = os.path.abspath(CONFIG['sandbox.run_dir'])

    if os.path.isdir(run_dir):
        LOG.debug(f'cleaning run directory')
        for item in pathlib.Path(run_dir).glob('*'):
            if item.is_file():
                item.unlink(missing_ok=True)
            elif item.is_dir():
                shutil.rmtree(item)
        LOG.debug(f'cleaned run directory')
    else:
        LOG.warning(f'skipped cleaning run directory: is not a directory')


def run_workspace(w, exit_cb: Callable) -> Union[None, threading.Thread]:
    """
    Prepare and execute a workspace program.
    :param w: A :class:Workspace or WID
    :param exit_cb: a callable with 4 arguments (rid, return_code, stdout, stderr)
    :return: a Thread instance or None
    """

    def _run_program(_intp: str,
                     _runp: str,
                     _workspace,
                     _txp: int,
                     _rxp: int,
                     _sim: bool,
                     _timeout: int,
                     _cb: Callable):
        program_args = [
            interpreter_path,
            run_path,
            '--screen-host',
            'localhost',
            '--tx-port',
            _txp,
            '--rx-port',
            _rxp
        ]

        if _sim:
            program_args.append('--simulate')

        args_text = ' '.join(program_args)
        LOG.info(f'executing "{args_text}"...')

        proc = subprocess.Popen(program_args)

        LOG.info(f'spawned PID {proc.pid}')

        # mark workspace as RUNNING
        with session.begin():
            workspace.run_status = RunStatus.RUNNING

        # create run log
        run_log = create_run_log(proc.pid,
                                 _intp,
                                 _runp,
                                 workspace=_workspace.wid,
                                 user=_workspace.owner.uid if _workspace.owner is not None else None)

        out, err = proc.communicate(timeout=_timeout)
        return_code = proc.returncode
        _cb(run_log.rid, return_code, out, err)

    workspace = coerce_workspace(w)

    LOG.debug(f'attempting to start workspace {workspace.short_wid}')
    if workspace is not None:
        # 1. Ensure needed filesystem paths still exist
        interpreter_path = workspace.interpreter_path

        if not os.path.exists(interpreter_path):
            LOG.error(f'workspace {workspace.short_wid}: interpreter does not exist at "{interpreter_path}"')
            return None

        storage_dir = workspace.storage_path
        storage_entrypoint_path = os.path.join(workspace.storage_path, workspace.py_file)
        if not os.path.exists(storage_entrypoint_path):
            LOG.error(f'workspace {workspace.short_wid}: entrypoint does not exist at "{storage_entrypoint_path}"')
            return None

        run_dir = workspace.run_dir
        if not os.path.isdir(run_dir):
            LOG.error(f'workspace {workspace.short_wid}: run directory does not exist at "{run_dir}"')
            return None

        run_path = os.path.join(run_dir, workspace.py_file)

        # mark workspace as STARTING
        with session.begin():
            workspace.run_status = RunStatus.STARTING

        # 2. Copy files from storage to run directory
        try:
            copy_tree(storage_dir,
                      run_dir,
                      preserve_mode=True,
                      preserve_times=True,
                      preserve_symlinks=False)
        except DistutilsError as e:
            LOG.error(f'copying program files to run environment failed: {str(e)}')
            clean_run_dir()
            return None

        # 3. Check if it can run on the big screen or simulator
        run_on_screen = False

        if workspace.run_privilege == RunTarget.SCREEN:
            run_on_screen = True

        # 4. If it can run on the screen, stop or pause pluggram, abort if another student program is running
        if run_on_screen:
            if ACTIVE_PLUGGRAM is not None:
                pause_pluggram(ACTIVE_PLUGGRAM, clear_screen=True)

            with session.begin():
                running = session.query(RunLog).filter(stopped_at=None).first()

                if running is not None:
                    if running.workspace is None:
                        LOG.warning(
                            f'tried to start workspace {workspace.short_wid} but something is currently running')
                    else:
                        LOG.warning(f'tried to start workspace {workspace.short_wid} but '
                                    f'another workspace is currently running ({running.workspace.short_wid})')
                    return None

        # 5. Start program with timeout (if set)
        timeout = workspace.max_runtime
        client_tx_port = utils.get_url_port(CONFIG['ipc.rx'])
        client_rx_port = utils.get_url_port(CONFIG['ipc.tx'])

        thread = threading.Thread(target=_run_program,
                                  args=[interpreter_path,
                                        run_path,
                                        workspace,
                                        client_tx_port,
                                        client_rx_port,
                                        not run_on_screen,
                                        timeout,
                                        exit_cb])
        thread.start()
        return thread
    return None


def program_exit_callback(rid: str, return_code: int, stdout, stderror):
    LOG.info(f'program exited naturally with return-code {return_code}')

    with session.begin():
        run_log = RunLog.query.get(rid)

    if run_log is not None:
        complete_run_log(run_log.rid,
                         ExitReason.NATURAL,
                         return_code,
                         stdout,
                         stderror)

        wid = run_log.workspace

        if wid is not None:
            workspace = coerce_workspace(wid)

            if workspace is not None:
                workspace.run_status = RunStatus.IDLE
    else:
        LOG.error(f'exit callback passed non-existent RID "{rid}"')


def stop_run_log(rid: str, user_action=False):
    with session.begin():
        run_log = RunLog.query.get(rid)

        if run_log is not None:
            LOG.debug(f'attempting to stop {run_log.short_rid}')

            # 1. Stop or kill process
            pid = run_log.pid
            os.kill(pid, signal.SIGKILL)
            LOG.info(f'sent SIGKILL to PID {pid} (run {run_log.short_rid})')

            # 2. Cleanup workspace (if any)
            wid = run_log.workspace
            if wid is not None:
                workspace = coerce_workspace(wid)

                if workspace is not None:
                    cleanup_workspace(workspace)

            # 3. Update run log
            complete_run_log(run_log.rid,
                             ExitReason.SYSTEM if not user_action else ExitReason.ADMIN,
                             None)
    raise RuntimeError('Bad RID')


def cleanup_workspace(w):
    workspace = coerce_workspace(w)
    # 1. Move files back to storage
    # 2. Update status
    # todo
    raise NotImplementedError()


def remove_workspace(w):
    with session.begin():
        workspace = coerce_workspace(w)

        if workspace is not None:
            LOG.debug(f'attempting to remove workspace {workspace.short_wid}')
            session.delete(workspace)
            shutil.rmtree(workspace.env_path, ignore_errors=True)
            LOG.debug(f'removing workspace: deleted environment directory {workspace.short_wid}')
            shutil.rmtree(workspace.storage_path, ignore_errors=True)
            LOG.debug(f'removing workspace: deleted storage directory {workspace.short_wid}')
            LOG.info(f'removed workspace {workspace.short_wid}')
            return True
    return False


def needs_setup() -> bool:
    with session.begin():
        count = session.query(User).count()

        if count < 2:
            return True
        else:
            return False


def shutdown():
    # todo: show message on screen

    if os.name == 'posix':
        args = ['poweroff']
        LOG.info(f'shutting down...')
        proc = subprocess.Popen(args)
        return_code = proc.wait(2)
        LOG.debug(f'poweroff return-code {return_code}')
    else:
        raise NotImplementedError('Intentionally left unimplemented; this system is only used on Linux, developed on '
                                  'Windows.')


def restart():
    # todo: show message on screen

    if os.name == 'posix':
        args = ['reboot']
        LOG.info(f'restarting...')
        proc = subprocess.Popen(args)
        return_code = proc.wait(2)
        LOG.debug(f'reboot return-code {return_code}')
    else:
        raise NotImplementedError('Intentionally left unimplemented; this system is only used on Linux')


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
    LOG.info(f'--- BEGINNING RESET ---')

    if keep_user is not None:
        assert isinstance(keep_user, User)
        LOG.debug(f'keeping account {keep_user.uid}')

    # 1. Open a new DB transaction
    with session.begin():
        run_logs = session.query(RunLog).all()

        # 2. Force stop all running screen programs
        for run_log in run_logs:
            if run_log.stopped_at is not None:
                stop_run_log(run_log.rid)

        workspaces = session.query(Workspace).all()
        # 3. Make backup of student code
        if archive_dir is not None:
            import zipfile

            os.makedirs(archive_dir, exist_ok=True)
            for workspace in workspaces:
                storage_dir = workspace.storage_path

                if os.path.isdir(storage_dir):
                    storage_files = list(pathlib.Path(storage_dir).rglob('*'))

                    if len(storage_files) > 0:
                        archive_date_code = dt.utcnow().strftime("%y%j")
                        workspace_user = workspace.owner

                        if workspace_user is not None:
                            archive_name = f'{archive_date_code}-U{workspace_user.uid}.zip'
                        else:
                            archive_name = f'{archive_date_code}-W{workspace.short_wid}.zip'

                        archive_path = os.path.join(archive_dir, archive_name)
                        archive = zipfile.ZipFile(archive_path, 'w')

                        manifest = {
                            'format': 1,
                            'system_version': VERSION,
                            'wid': workspace.wid,
                            'uid': workspace_user.uid if workspace_user is not None else None,
                            'created_at': workspace.created_at.isoformat(),
                            'opened_at': workspace.opened_at.isoformat(),
                            'archived_at': dt.utcnow().isoformat(),
                            'entrypoint': workspace.py_file,
                            'interpreter': pathlib.Path(workspace.interpreter_path).name,
                            'path_count': len(storage_files)
                        }
                        manifest_text = json.dumps(manifest)
                        zip_info = zipfile.ZipInfo('manifest.json')
                        zip_info.compress_type = zipfile.ZIP_DEFLATED
                        archive.writestr(zip_info, manifest_text)

                        for storage_file in storage_files:
                            if os.path.exists(storage_file):
                                archive.write(storage_file, compress_type=zipfile.ZIP_DEFLATED)

                        archive.close()
                        LOG.debug(f'archived workspace {workspace.short_wid} '
                                  f'({len(storage_files)} files to "{archive_name}")')
                    else:
                        LOG.debug(f'workspace {workspace.short_wid} has no files to archive')
                else:
                    LOG.warning(f'skipping archive of workspace {workspace.short_wid}: '
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

    LOG.info(f'--- RESET COMPLETED ---')
