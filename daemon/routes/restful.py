import logging
from flask import Blueprint, request
from flask_restful import Api, Resource
from common import LIMITER, CONFIG
from .authentication import auth_endpoint_allowed, get_auth_status
from utils import enum_name_or_null, isoformat_or_null
from models import (User,
                    RunTarget,
                    UserType,
                    Workspace)
import system

LOG = logging.getLogger('ledscreen.web.api')
bp = Blueprint('api', __name__, url_prefix='/api')
api = Api(bp)


class ResetSystem(Resource):
    decorators = [LIMITER.limit("1/minute")]

    def get(self):
        auth_result = get_auth_status()

        if auth_result is not None and auth_result.valid:
            system.reset(keep_user=auth_result.user, archive_dir=CONFIG['app.archive_dir'])

            try:
                system.restart()
            except:
                LOG.info('requesting system restart failed')
                pass

            return {}, 200

        return {}, 403


api.add_resource(ResetSystem, '/system/reset')


class Workspaces(Resource):
    decorators = [LIMITER.limit("10/minute")]

    def get(self, wid: str):
        if not auth_endpoint_allowed(minimum_credential=UserType.ADMIN):
            return {}, 403

        workspace = Workspace.query.get(wid)

        if workspace is None:
            return {}, 404

        payload = {
            'wid': workspace.wid,
            'created_at': isoformat_or_null(workspace.created_at),
            'opened_at': isoformat_or_null(workspace.opened_at),
            'run_privilege': enum_name_or_null(workspace.run_privilege),
            'max_runtime': workspace.max_runtime,
            'run_target': enum_name_or_null(workspace.run_target),
            'run_status': workspace.run_status.name,
            'owner': workspace.owner
        }
        return payload, 200

    def delete(self, wid: str):
        if not auth_endpoint_allowed(minimum_credential=UserType.ADMIN):
            return {}, 403

        result = system.remove_workspace(wid)

        return {'success': result, 'wid': wid}, 200


api.add_resource(Workspaces, '/workspace/<wid>')


class CreateWorkspace(Resource):
    decorators = [LIMITER.limit("10/minute")]

    def post(self):
        if not auth_endpoint_allowed(minimum_credential=UserType.ADMIN):
            return {}, 403

        content_length = request.content_length

        content = None
        if content_length > 0:
            if content_length > 100000:
                return {'message': 'file too large; max 100kB'}, 413

            content = request.get_data(as_text=True)

        owner_text = request.args.get('owner')
        owner_uid = None

        if owner_text is not None:
            owner = User.query.get(owner_text)

            if owner is None:
                return {'message': 'UID not found'}, 400
            else:
                owner_uid = owner.uid

        run_privilege_text = request.args.get('run_privilege')
        run_privilege = None

        if run_privilege_text is not None:
            try:
                run_privilege = RunTarget[run_privilege_text.upper()]
            except ValueError:
                return {'message': 'unknown run privilege'}, 400

        max_runtime_text = request.args.get('max_runtime')
        max_runtime = None

        if max_runtime_text is not None:
            try:
                max_runtime = int(max_runtime_text)
            except ValueError:
                return {'message': 'cannot parse max_runtime'}, 400

        envs_dir = CONFIG['sandbox.envs_dir']
        storage_dir = CONFIG['sandbox.storage_dir']
        run_dir = CONFIG['sandbox.run_dir']
        py_filename = CONFIG['sandbox.entrypoint']

        workspace = system.create_workspace(envs_dir,
                                            storage_dir,
                                            run_dir,
                                            py_filename,
                                            py_contents=content,
                                            owner=owner_uid,
                                            run_privilege=run_privilege,
                                            max_runtime=max_runtime)
        return {'wid': workspace.wid}, 200


api.add_resource(CreateWorkspace, '/workspace')


class LoginProbe(Resource):
    decorators = [LIMITER.limit("20/minute")]

    def get(self):
        code_parameter = request.args.get('code')

        if code_parameter is None:
            return {}, 400

        user = User.query.get(code_parameter)
        if user is not None:
            # todo: if user is logged in, show more data

            payload = {
                'locked': user.locked,
                'requires_password': user.password is not None
            }
            return payload, 200
        else:
            return {}, 404


api.add_resource(LoginProbe, '/auth/probe')
