import logging
from flask import Blueprint, request
from flask_restful import Api, Resource, abort
import system
import pluggram


LOG = logging.getLogger('ledscreen.web.api')
bp = Blueprint('api', __name__, url_prefix='/api')
api = Api(bp)


def key_or_session():
    api_key = request.args.get('key', None)

    if api_key is not None:
        if api_key not in system.config['app.api_keys']:
            LOG.debug(f'API key "{api_key}" not found, checking for cookie instead')

            if system.is_user_authenticated():
                return True
            else:
                return False
        else:
            LOG.info(f'API key "{api_key}" was used for "{request.path}"')
            return True
    return False


class RunPluggram(Resource):

    def post(self, query_name: str):
        if not key_or_session():
            return {}, 403

        meta = None

        for pg in system.loaded_pluggrams:
            if pg.name == query_name.lower().strip():
                meta = pg
                break

        if meta is None:
            return {'query_name': query_name}, 404
        else:
            pluggram.start_pluggram(meta, system.screen)
            return {'query_name': query_name}, 200


api.add_resource(RunPluggram, '/pluggram/<name>/run')


class PausePluggram(Resource):

    def post(self):
        if not key_or_session():
            return {}, 403

        clear_arg = request.args.get('clear', False)

        try:
            clear = bool(clear_arg)
        except ValueError:
            return {'message': 'cannot parse "clear" argument'}, 400

        pluggram.pause_pluggram()

        if clear:
            system.screen.clear()

        return {}, 200


api.add_resource(PausePluggram, '/pluggrams/pause')


class RunningPluggram(Resource):

    def get(self):
        name = None

        if pluggram.RUNNING_PLUGGRAM_META is not None:
            name = pluggram.RUNNING_PLUGGRAM_META.name

        return {'name': name}, 200


api.add_resource(RunningPluggram, '/pluggrams/running')


class Pluggrams(Resource):

    def get(self):
        payload = []

        for pg in system.loaded_pluggrams:
            options_node = []

            for opt in pg.options:
                option_node = {
                    'name': opt.key,
                    'type': opt.type_name,
                    'min': opt.min,
                    'max': opt.max,
                    'choices': opt.choices,
                    'default_value': opt.default
                }
                options_node.append(option_node)

            pluggram_node = {
                'name': pg.name,
                'display_name': pg.display_name,
                'version': pg.version,
                'description': pg.description,
                'options': options_node
            }
            payload.append(pluggram_node)

        return payload, 200


api.add_resource(Pluggrams, '/pluggrams')


class SystemRestart(Resource):

    def post(self):
        if not key_or_session():
            return {}, 403

        try:
            system.restart()
            return {}, 202
        except:
            LOG.warning('requesting system restart failed')

        return {}, 200


api.add_resource(SystemRestart, '/system/restart')


class SystemPoweroff(Resource):

    def post(self):
        if not key_or_session():
            return {}, 403

        try:
            system.shutdown()
            return {}, 202
        except:
            LOG.warning('requesting system shutdown failed')

        return {}, 200


api.add_resource(SystemPoweroff, '/system/poweroff')
