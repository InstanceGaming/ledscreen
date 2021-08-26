import logging
from flask import Blueprint, request
from flask_restful import Api, Resource
import system
from common import config, screen, pluggram_manager


LOG = logging.getLogger('ledscreen.web.api')
bp = Blueprint('api', __name__, url_prefix='/api')
api = Api(bp)


def key_or_session():
    if system.is_user_authenticated():
        return True
    else:
        api_key = request.args.get('key', None)

        if api_key is not None:
            if api_key not in config['app.api_keys']:
                LOG.debug(f'API key "{api_key}" not found, checking for cookie instead')
            else:
                LOG.info(f'API key "{api_key}" was used for "{request.path}"')
                return True
        return False


def get_query_pluggram_name(query_name: str):
    selected_name = None

    for pg in pluggram_manager.get_names():
        if pg == query_name.lower().strip():
            selected_name = pg
            break

    return selected_name


class RunPluggram(Resource):

    def post(self, query_name: str):
        if not key_or_session():
            return {}, 403

        selected_name = get_query_pluggram_name(query_name)

        if selected_name is None:
            return {'query_name': query_name}, 404
        else:
            pluggram_manager.start(selected_name)
            return {'query_name': query_name}, 200


api.add_resource(RunPluggram, '/pluggram/<query_name>/run')


class StopPluggram(Resource):

    def post(self):
        if not key_or_session():
            return {}, 403

        clear_arg = request.args.get('clear', False)

        try:
            clear = bool(clear_arg)
        except ValueError:
            return {'message': 'cannot parse "clear" argument'}, 400

        running_name = pluggram_manager.get_running()

        if running_name:
            pluggram_manager.stop()

            if clear:
                screen.clear()

        return {'name': running_name}, 200


api.add_resource(StopPluggram, '/pluggrams/stop')


class PluggramOptions(Resource):

    def post(self, query_name: str):
        if not key_or_session():
            return {}, 403

        selected_name = get_query_pluggram_name(query_name)

        if selected_name is None:
            return {'query_name': query_name}, 404
        else:
            values = {}
            options = pluggram_manager.get_options(selected_name)
            keys = [o.name for o in options]

            for key, value in request.values.items():
                key = key.lower()

                if key in keys:
                    try:
                        value = int(value)
                    except ValueError:
                        pass

                    values.update({key: value})

            invalid_keys, saved = pluggram_manager.save_options(selected_name, values)
            display_name = pluggram_manager.get_info(selected_name).display_name

            return {'query_name': query_name,
                    'display_name': display_name,
                    'invalid_keys': invalid_keys,
                    'saved': saved}, 200


api.add_resource(PluggramOptions, '/pluggram/<query_name>/options')


class RunningPluggram(Resource):

    def get(self):
        running_name = pluggram_manager.get_running()
        return {'name': running_name}, 200


api.add_resource(RunningPluggram, '/pluggrams/running')


class Pluggrams(Resource):

    def get(self):
        payload = []

        for name in pluggram_manager.get_names():
            options = pluggram_manager.get_options(name)
            options_node = []

            for opt in options:
                option_node = {
                    'name': opt.name,
                    'type': opt.type_name,
                    'min': opt.min,
                    'max': opt.max,
                    'choices': opt.choices,
                    'default_value': opt.default,
                    'value': opt.value
                }
                options_node.append(option_node)

            info = pluggram_manager.get_info(name)
            pluggram_node = {
                'name': name,
                'display_name': info.display_name,
                'version': info.version,
                'description': info.description,
                'options': options_node
            }
            payload.append(pluggram_node)

        return payload, 200


api.add_resource(Pluggrams, '/pluggrams')


class Fonts(Resource):

    def get(self):
        names = screen.font_names()
        return names, 200


api.add_resource(Fonts, '/fonts')


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
