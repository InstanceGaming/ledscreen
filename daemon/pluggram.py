import os
import logging
import importlib.util
import traceback as tb
from enum import IntEnum
from inspect import signature
from api import Screen


class ProgramStatus(IntEnum):
    OFF = 0
    RUNNING = 1
    OVERRIDDEN = 2


class Option:
    SUPPORTED_TYPES = [int, str, bool]
    
    @property
    def key(self):
        return self._key
    
    @property
    def type(self):
        return type(self._default)

    @property
    def default(self):
        return self._default
    
    @property
    def min(self):
        return self._min
    
    @property
    def max(self):
        return self._max
    
    @property
    def choices(self):
        return self._choices

    def __init__(self, key: str, default, **kwargs):
        self._key = key
        self._default = default
        self._min = None
        self._max = None
        self._choices = None

        if self.type not in self.SUPPORTED_TYPES:
            raise TypeError(f'unsupported option type {self.type}')

        if self.type == str:
            choices = kwargs.get('choices')

            if choices is not None:
                if isinstance(choices, list):
                    self._choices = choices
                else:
                    raise TypeError('choices must be of type list')
        elif self.type == int:
            min_val = kwargs.get('min')

            if min_val is not None:
                if isinstance(min_val, int):
                    self._min = min_val
                else:
                    raise TypeError('min value must be an integer')

            max_val = kwargs.get('max')

            if max_val is not None:
                if isinstance(max_val, int):
                    if min_val is not None:
                        if max_val > min_val:
                            raise ValueError('max value larger than min value')

                    self._max = max_val
                else:
                    raise TypeError('max value must be an integer')

    def __repr__(self):
        return f'<Option "{self._key}" {self.type} default={self._default}>'

    def validate(self, o):
        if isinstance(o, str):
            if self._choices is not None:
                if o in self._choices:
                    return True
            else:
                return True
        elif isinstance(o, int):
            min_ok = False

            if self._min is not None:
                if o > self._min:
                    min_ok = True
            else:
                min_ok = True

            max_ok = False

            if self._max is not None:
                if o <= self._max:
                    max_ok = True
            else:
                max_ok = True

            return min_ok and max_ok
        return isinstance(o, self.type)


class Pluggram:

    @property
    def module_path(self):
        return self._path
    
    @property
    def name(self):
        return self._name

    @property
    def display_name(self):
        return self._display_name
    
    @property
    def description(self):
        return self._description
    
    @property
    def entrypoint(self):
        return self._entrypoint
    
    @property
    def status(self):
        return self._status
    
    def __init__(self,
                 module,
                 module_path: str,
                 run_parameters,
                 name: str,
                 display_name: str,
                 description: str,
                 version: str,
                 entrypoint: str,
                 options=None):
        self._module = module
        self._run_parameters = run_parameters
        self._path = module_path
        self._name = name
        self._display_name = display_name
        self._description = description
        self._version = version
        self._entrypoint = entrypoint
        self._options = options or []
        self._option_values = self.get_default_options()
        self._status = ProgramStatus.OFF

    def get_default_options(self):
        opts = {}

        for option in self._options:
            opts.update({option.key: option.default})

        return opts

    def init(self, *args, **kwargs):
        arg_count = len(self._run_parameters)

        if len(args) < arg_count - 1:
            raise RuntimeError(f'Argument mismatch (wants {arg_count})')

        self._status = ProgramStatus.RUNNING
        self._module.run(self._option_values, *args, **kwargs)

    def override(self, active: bool):
        if self._status == ProgramStatus.OFF:
            raise RuntimeError('Cannot override program that is off')

        self._status = ProgramStatus.OVERRIDDEN if active else self._status

    def tick(self):
        if self._status == ProgramStatus.OFF:
            raise RuntimeError('Not initialized, did you call init()?')

        if self._status != ProgramStatus.OVERRIDDEN:
            self._module.tick()

    def stop(self):
        self._status = ProgramStatus.OFF


def _has_function(mod, name):
    return name in dir(mod) and callable(getattr(mod, name, None))


def load(programs_dir: str):
    if not os.path.isdir(programs_dir):
        raise RuntimeError('Programs directory does not exist or is not a directory')

    pluggrams = []

    for _, dirs, _ in os.walk(programs_dir, topdown=True, followlinks=False):
        for module_name in dirs:
            module_path = os.path.abspath(os.path.join(programs_dir, module_name))
            if os.path.exists(module_path):
                for file in os.listdir(module_path):
                    if file == '__init__.py':
                        init_path = os.path.join(module_path, file)
                        logging.debug(f'found module {module_name} ("{module_path}")')

                        spec = importlib.util.spec_from_file_location(module_name, init_path)
                        m = importlib.util.module_from_spec(spec)

                        try:
                            spec.loader.exec_module(m)
                        except Exception as e:
                            message = f'disqualifying module {module_name}: exception raised in "{file}":\n'
                            message += ''.join(tb.format_exception(None, e, e.__traceback__))
                            logging.info(message)
                            continue

                        if hasattr(m, '__pluggram__'):
                            metadata = m.__pluggram__

                            display_name = metadata.get('display_name')
                            description = metadata.get('description')
                            version = metadata.get('version')
                            entrypoint = metadata.get('entrypoint')
                            options = metadata.get('options')

                            if entrypoint is not None:
                                entrypoint_path = os.path.join(module_path, entrypoint)

                                if not os.path.isfile(entrypoint_path):
                                    logging.debug(f'disqualifying module {module_name}: entrypoint does not exist')
                                    continue
                            else:
                                entrypoint = init_path

                            if display_name is None or options is None:
                                logging.debug(f'disqualifying module {module_name}: incomplete "__pluggram__" dict')
                                continue

                            if not isinstance(options, list):
                                logging.debug(f'disqualifying module {module_name}: metadata options must be a list type')
                                continue
                            else:
                                for option in options:
                                    if not isinstance(option, Option):
                                        logging.debug(f'disqualifying module {module_name}: metadata option must be of '
                                                      f'pluggram.Option type')
                                        continue

                            if not _has_function(m, 'run'):
                                logging.debug(f'disqualifying module {module_name}: does not define run()')
                                continue
                            else:
                                run_sig = signature(m.run)
                                run_parameters = run_sig.parameters

                                if len(run_parameters) < 1:
                                    logging.debug(f'disqualifying module {module_name}: '
                                                  'run() signature needs at least one argument (to pass options)')
                                    continue

                            if not _has_function(m, 'tick'):
                                logging.debug(f'disqualifying module {module_name}: does not define tick()')
                                continue

                            program = Pluggram(m,
                                               module_path,
                                               run_parameters,
                                               module_name,
                                               display_name,
                                               description,
                                               version,
                                               entrypoint,
                                               options)
                            pluggrams.append(program)
                            logging.info(f'loaded module {module_name} ("{module_path}")')
                        else:
                            logging.debug(f'disqualifying module {module_name}: does not define "__pluggram__"')

    return pluggrams
