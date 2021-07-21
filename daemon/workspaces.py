import enum
import os
import subprocess
import logging
import sys

import utils


class WorkspaceManager:

    @property
    def workspaces(self):
        return self._workspaces

    @property
    def entrypoint_file(self):
        return self._entrypoint_file

    @property
    def run_dir(self):
        return self._run_dir

    @property
    def run_user_id(self):
        return self._run_user_id

    @property
    def run_group_id(self):
        return self._run_group_id

    @property
    def interpreter_filename(self):
        return self._interpreter_filename

    def __init__(self,
                 environments_dir: str,
                 storage_dir: str,
                 run_user_id: int,
                 run_group_id: int,
                 run_dir: str,
                 interpreter_filename: str):
        self._logger = logging.getLogger()
        self._envs_dir = environments_dir
        self._store_dir = storage_dir

        if not os.path.isdir(self._envs_dir):
            raise RuntimeError('Environments path does not exist or is not a directory')

        self._run_user_id = run_user_id
        self._run_group_id = run_group_id
        self._run_dir = run_dir

        if not os.path.isdir(self._run_dir):
            raise RuntimeError('Run path does not exist or is not a directory')

        self._interpreter_filename = interpreter_filename
        self._entrypoint_file = "main.py"
        self._workspaces = []

    def get_by_wid(self, wid: str):
        for ws in self._workspaces:
            if ws.wid == wid:
                return ws
        return None

    def create(self):
        wid = ''
        wid_text = wid
        wid_text_short = wid_text[:16]
        env_dir = os.path.abspath(os.path.join(self._envs_dir, wid_text))
        logging.debug(f'workspace "{wid_text_short}" environment will be located at "{env_dir}"')

        if not mk_virtual_env(env_dir, wid_text_short):
            raise RuntimeError('virtualenv failed: non-zero exit code')

        env_bin_dir = os.path.abspath(get_virtualenv_bin(env_dir))
        logging.debug(f'workspace "{wid_text_short}" environment binary directory is located at "{env_bin_dir}"')

        # todo: add user ID to environment (in a .py or .json file?)
        # todo: create storage folder for workspace and create default entrypoint from template.
        store_dir = os.path.abspath(self._store_dir)

        logging.debug(f'workspace "{wid_text_short}" storage will be located at "{store_dir}"')
        try:
            os.mkdir(store_dir)
        except OSError as e:
            logging.error(f'failed to make storage directory: {str(e)}')
            raise e

        workspace = Workspace(wid, self, env_bin_dir, store_dir)
        self._workspaces.append(workspace)
        return workspace

    def remove(self, workspace, purge: bool, stop_timeout=None):
        if workspace is not None:
            if workspace.status == WorkspaceStatus.RUNNING:
                workspace.stop(timeout=stop_timeout)

            if purge:
                workspace.purge()

            self._workspaces.remove(workspace)
            logging.info(f'removed workspace "{workspace.short_wid}" ({purge=})')
            return True

        return False


class WorkspaceStatus(enum.IntFlag):
    IDLE = enum.auto()
    STARTING = enum.auto()
    RUNNING = enum.auto()
    STOPPING = enum.auto()
    PURGING = enum.auto()


class Workspace:

    @property
    def wid(self):
        return self._wid

    @property
    def short_wid(self):
        return self._wid[:16]

    @property
    def status(self):
        return self._status

    @property
    def bin_dir(self):
        return self._bin_dir

    def __init__(self,
                 wid: str,
                 manager: WorkspaceManager,
                 bin_dir: str,
                 storage_dir: str):
        self._wid = wid
        self._manager = manager
        self._bin_dir = bin_dir
        self._store_dir = storage_dir
        self._status = WorkspaceStatus.IDLE
        self._process = None

    def run(self, simulate: bool, timeout=None):
        logging.info(f'start workspace "{self.short_wid}" ({simulate=}, {timeout=})')

        interpreter_filename = self._manager.interpreter_filename
        interpreter_path = os.path.abspath(os.path.join(self._bin_dir, interpreter_filename))
        logging.debug(f'workspace "{self.short_wid}" interpreter is located at "{interpreter_path}"')

        # todo: check storage location exists; give different warning if entrypoint is not in storage
        if not os.path.isdir(self._store_dir):
            logging.error(f'workspace "{self.short_wid}" does not have a storage directory')
            return False

        entrypoint_file = self._manager.entrypoint_file
        entrypoint_path = os.path.abspath(os.path.join(self._manager.run_dir, entrypoint_file))
        logging.debug(f'workspace "{self.short_wid}" final entrypoint is located at "{entrypoint_path}"')

        if os.path.isfile(entrypoint_path):
            self._status = WorkspaceStatus.STARTING
            self._process = utils.popen_with_callback([interpreter_path, entrypoint_path],
                                                      self._completion_cb,
                                                      timeout)
            self._status = WorkspaceStatus.RUNNING
            logging.info(f'workspace "{self.short_wid}" has forked')
            return True
        else:
            logging.error(f'workspace "{self.short_wid}" entrypoint does not exist')
        return False

    def _done(self):
        logging.info(f'workspace "{self.short_wid}" cleaning up...')

    def _completion_cb(self, process):
        return_code = process.returncode
        logging.info(f'workspace "{self.short_wid}" has finished naturally with return code {return_code}')
        self._done()

    def stop(self, timeout=None):
        self._status = WorkspaceStatus.STOPPING
        self._done()

    def kill(self):
        self._status = WorkspaceStatus.IDLE
        self._done()

    def purge(self):
        self._status = WorkspaceStatus.PURGING

    def __repr__(self):
        return f'<Workspace "{self.short_wid}" status={self._status}>'
