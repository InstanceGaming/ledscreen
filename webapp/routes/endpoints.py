import logging
import os
from typing import Optional

from flask import Blueprint, request
from flask_restful import Api, Resource, abort
import system
import pluggram


LOG = logging.getLogger('ledscreen.web.api')
bp = Blueprint('api', __name__, url_prefix='/api')
api = Api(bp)


def key_or_session():
    if system.is_user_authenticated():
        return True
    else:
        api_key = request.args.get('key', None)

        if api_key is not None:
            if api_key not in system.config['app.api_keys']:
                LOG.debug(f'API key "{api_key}" not found, checking for cookie instead')
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
            pluggram.runner.start(meta, system.screen)
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

        if pluggram.runner.running:
            meta = pluggram.runner.meta
            pluggram.runner.stop()

            if clear:
                system.screen.clear()

            return {'name': meta.name}, 200
        return {'name': None}, 200


api.add_resource(StopPluggram, '/pluggrams/stop')


class PluggramOptions(Resource):

    def post(self, query_name: str):
        if not key_or_session():
            return {}, 403

        meta: Optional[pluggram.PluggramMeta] = None

        for pg in system.loaded_pluggrams:
            if pg.name == query_name.lower().strip():
                meta = pg
                break

        if meta is None:
            return {'query_name': query_name}, 404
        else:
            values = {}
            keys = [o.key for o in meta.options]

            for key, value in request.values.items():
                key = key.lower()

                if key in keys:
                    try:
                        value = int(value)
                    except ValueError:
                        pass

                    values.update({key: value})

            invalid_keys = meta.validate_options(values)
            saved_keys = []

            if len(invalid_keys) < 1:
                saved_keys = meta.save_options(values)

            did_save = len(saved_keys) > 0 and len(values.keys()) > 0
            return {'query_name': query_name,
                    'display_name': meta.display_name,
                    'invalid_keys': invalid_keys,
                    'saved': did_save}, 200


api.add_resource(PluggramOptions, '/pluggram/<query_name>/options')


class RunningPluggram(Resource):

    def get(self):
        if pluggram.runner.running:
            meta = pluggram.runner.meta
            return {'name': meta.name, 'display_name': meta.display_name}, 200
        return {'name': None, 'display_name': None}, 200


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
                    'default_value': opt.default,
                    'value': opt.value
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


class Fonts(Resource):

    def get(self):
        font_dir = system.config['screen.fonts_dir']
        abs_path = os.path.abspath(font_dir)

        if os.path.isdir(abs_path):
            files = os.listdir(abs_path)
            return files, 200
        else:
            return [], 404


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
