import enum
import json
import numbers
import os
import logging
import importlib.util
import traceback
import traceback as tb
import inspect
import re
import threading
from collections import KeysView
from multiprocessing import Event
from inspect import Parameter
from typing import Optional, Tuple

from utils import timing_counter

LOG = logging.getLogger('ledscreen.pluggram')
INTERVAL_PATTERN = re.compile(r'(\d+)(ms|s|m)')
OPT_KEY_PATTERN = re.compile(r'(^a-z0-9_)')
USER_OPTIONS_FILE = 'options.json'


def parse_interval_text(raw_value):
    """
    Get millisecond rate from text.

    :param raw_value: input text.
    :return: None for None and 0, -1 if no regex
    match, -2 if number less than 0, -3 for number
    parse failure and -4 for unknown multiplier
    abbreviation.
    """

    if raw_value is None:
        return None

    stripped = raw_value.strip()
    m = INTERVAL_PATTERN.match(stripped)
    if m:
        number_text = m.group(1)
        multiplier_text = m.group(2)

        try:
            number = int(number_text)

            if number < 0:
                return -2
        except ValueError:
            return -3

        if multiplier_text == 'ms':
            return number
        elif multiplier_text == 's':
            return number * 1000
        elif multiplier_text == 'm':
            return number * 60000
        else:
            return -4
    return -1


class InputMethod(enum.IntEnum):
    DEFAULT = 0
    COLOR_PICKER = 1


class Option:
    SUPPORTED_TYPES = [int, float, str, bool]

    @property
    def key(self):
        return self._key

    @property
    def display_name(self):
        return self.key.replace('_', ' ').capitalize()

    @property
    def markup_id(self):
        return self.key.replace('_', '-').lower()

    @property
    def type(self):
        return type(self.default)

    @property
    def type_name(self):
        return self.type.__name__.upper()

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
    def help_text(self):
        return self._help_text

    @property
    def choices(self):
        return self._choices
    
    @property
    def input_method(self):
        return self._input_method
    
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        if not self.validate(v):
            raise ValueError('not valid')
        self._value = v

    def __init__(self, key: str, default, **kwargs):
        self._key = key

        if OPT_KEY_PATTERN.match(key):
            raise ValueError(f'"{key}" is invalid (matched with pattern "{OPT_KEY_PATTERN.pattern}")')

        self._default = default
        self._min = None
        self._max = None
        self._choices = None
        self._help_text = kwargs.get('help')
        self._input_method = InputMethod.DEFAULT
        self._value = default

        if self.type not in self.SUPPORTED_TYPES:
            raise TypeError(f'unsupported option type {self.type}')

        if not self.validate(default):
            raise ValueError(f'Default value of option "{key}" is invalid')

        min_val = kwargs.get('min')
        max_val = kwargs.get('max')

        if self.type == str:
            choices = kwargs.get('choices')

            if choices is not None:
                if isinstance(choices, list):
                    if default not in choices:
                        raise ValueError('default value not present in choices')

                    self._choices = choices
                else:
                    raise TypeError('choices must be of type list')

            if min_val is not None:
                if isinstance(min_val, int):
                    if min_val < 1:
                        raise ValueError('min value for string must be at least 1')

                    self._min = min_val
                else:
                    raise TypeError('min value must be an integer')

            if max_val is not None:
                if isinstance(max_val, int):
                    if min_val is not None:
                        if max_val < min_val:
                            raise ValueError('max value less than min value')

                    self._max = max_val
                else:
                    raise TypeError('max value must be an integer')
        elif self.type == int or self.type == float:
            if kwargs.get('color_picker'):
                if self.type == float:
                    raise ValueError('cannot use color picker dialog for float type')

                self._input_method = InputMethod.COLOR_PICKER

            if min_val is not None:
                if isinstance(min_val, (int, float)):
                    self._min = min_val
                else:
                    raise TypeError('min value must be an integral')

            if max_val is not None:
                if isinstance(max_val, (int, float)):
                    if min_val is not None:
                        if type(max_val) != type(min_val):
                            raise ValueError('min/max values must be the same type')

                        if max_val < min_val:
                            raise ValueError('max value less than min value')

                    self._max = max_val
                else:
                    raise TypeError('max value must be an integral')

    def __repr__(self):
        return f'<Option "{self._key}" {self.type_name} default={self._default} value={self._value}>'

    def validate(self, o):
        if not isinstance(o, self.type):
            return False

        if isinstance(o, str):
            if self._choices is not None:
                if o in self._choices:
                    return True
            else:
                if self._min is not None:
                    if len(o) < self._min:
                        return False
                if self._max is not None:
                    if len(o) > self._max:
                        return False

                return True
        elif isinstance(o, int):
            min_ok = False

            if self._min is not None:
                if o >= self._min:
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
        raise NotImplementedError()


class PluggramMeta:

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
    def class_name(self):
        return self._class_name

    @property
    def version(self):
        return self._version

    @property
    def description(self):
        return self._description

    @property
    def options(self):
        return self._options
    
    @property
    def tick_rate(self):
        return self._tick_rate

    @property
    def has_user_options(self):
        return os.path.exists(self._store_path)

    @property
    def type(self):
        return self._entry_class

    @property
    def initialized(self):
        return self._instance is not None

    def __init__(self,
                 module,
                 module_path: str,
                 entry_class: type,
                 tick_rate: int,
                 name: str,
                 class_name: str,
                 display_name: str,
                 description: str,
                 version: str,
                 positional_count: int,
                 options=None):
        self._module = module
        self._path = module_path
        self._entry_class = entry_class
        self._class_name = class_name
        self._tick_rate = tick_rate
        self._name = name
        self._display_name = display_name
        self._description = description
        self._version = version
        self._positional_count = positional_count
        self._options = options or []
        self._store_path = os.path.join(self.module_path, USER_OPTIONS_FILE)
        self._last_init_params: Optional[Tuple[list, dict]] = None
        self._instance = None

    def validate_options(self, options: dict) -> list:
        invalid_keys = []
        for key, value in options.items():
            for option in self._options:
                if option.key == key:
                    if not option.validate(value):
                        invalid_keys.append(key)
                    break

        return invalid_keys

    def save_options(self, options: dict) -> KeysView:
        store_obj = {}
        previous_value = None
        for key, value in options.items():
            for opt in self._options:
                if opt.key == key:
                    previous_value = opt.value
                    opt.value = value
                    break
            else:
                raise KeyError(f'Key "{key}" cannot be mapped to Option')

            if previous_value is None or (value != previous_value):
                store_obj.update({key: value})

        with open(self._store_path, 'w') as sf:
            json.dump(store_obj, sf)

        return store_obj.keys()

    def load_options(self):
        with open(self._store_path, 'r') as sf:
            root_node: dict = json.load(sf)

        for key, value in root_node.items():
            for opt in self._options:
                if key == opt.key:
                    if value != opt.default:
                        try:
                            opt.value = value
                        except ValueError:
                            LOG.warning(f'Validation failed for user option "{key}" from file, using default value')
                            continue
                    break

    def init(self, *args, **kwargs):
        if len(args) < self._positional_count:
            raise RuntimeError(f'Argument mismatch (wants {self._positional_count})')

        options = {}

        known_keys = [o.key for o in self._options]
        for key, value in kwargs.items():
            if key in known_keys:
                known_keys.remove(key)
                for option in self._options:
                    if option.key == key:
                        if option.validate(value):
                            options.update({key: value})
                        else:
                            raise ValueError(f'Option "{key}" has invalid value')
                        break

        for unset_key in known_keys:
            for option in self._options:
                if option.key == unset_key:
                    if unset_key not in options.keys():
                        options.update({unset_key: option.value})
                        break

        self._instance = self._entry_class(*args, **options)

    def reload(self):
        if self._last_init_params is None:
            raise RuntimeError('Cannot reload pluggram that was never initialized')

        args = self._last_init_params[0]
        kwargs = self._last_init_params[1]

        if len(args) > 0:
            self.init(*args, **kwargs)
        else:
            self.init(**kwargs)

    def tick(self):
        if self._instance is None:
            raise RuntimeError('cannot tick() as pluggram was never initialized')

        self._instance.tick()


class Pluggram:

    def tick(self):
        raise NotImplementedError('tick() was never overridden')


def load(programs_dir: str, argument_count):
    if not os.path.isdir(programs_dir):
        raise RuntimeError('Programs directory does not exist or is not a directory')

    pluggram_metas = []

    for _, dirs, _ in os.walk(programs_dir, topdown=True, followlinks=False):
        for module_name in dirs:
            module_path = os.path.abspath(os.path.join(programs_dir, module_name))
            if os.path.exists(module_path):
                for file in os.listdir(module_path):
                    if file == '__init__.py':
                        init_path = os.path.join(module_path, file)
                        LOG.debug(f'found module {module_name} ("{module_path}")')

                        spec = importlib.util.spec_from_file_location(module_name, init_path)
                        loaded_module = importlib.util.module_from_spec(spec)

                        try:
                            spec.loader.exec_module(loaded_module)
                        except Exception as e:
                            message = f'disqualifying module {module_name}: exception raised in "{file}":\n'
                            message += ''.join(tb.format_exception(None, e, e.__traceback__))
                            LOG.warning(message)
                            continue

                        # 1. get class definitions in module to find entrypoint
                        class_members = inspect.getmembers(loaded_module, inspect.isclass)

                        module_class = None
                        # 2. find one class which inherits Pluggram or DQ
                        for class_name, module_class in class_members:
                            bases = module_class.__bases__

                            if Pluggram in bases:
                                break

                        if module_class is None:
                            LOG.warning(f'disqualifying module {module_name}: '
                                        'module does not define a class inheriting Pluggram')
                            continue

                        # 3. ensure the class has a constructor and tick()
                        init_func = getattr(module_class, '__init__', None)

                        if not callable(init_func):
                            LOG.warning(f'disqualifying {module_name}.{class_name}: '
                                        'does not define constructor')
                            continue

                        tick_func = getattr(module_class, 'tick', None)

                        if not callable(tick_func):
                            LOG.warning(f'disqualifying {module_name}.{class_name}: '
                                        'does not define tick() method')
                            continue

                        # 4. note argument count
                        construct_parameters = inspect.signature(module_class.__init__).parameters
                        positional_count = 0

                        for parameter in construct_parameters.values():
                            if parameter.name != 'self':
                                if parameter.kind == Parameter.POSITIONAL_ONLY and parameter.default == Parameter.empty:
                                    positional_count += 1

                        if positional_count > argument_count:
                            LOG.warning(f'disqualifying {module_name}.{class_name}: '
                                        f'constructor positional arguments mismatch ({positional_count} wanted, '
                                        f'{argument_count} given)')
                            continue

                        # 5. collect metadata
                        display_name = module_name
                        if hasattr(module_class, 'DISPLAY_NAME'):
                            display_name = str(module_class.DISPLAY_NAME)

                        description = None
                        if hasattr(module_class, 'DESCRIPTION'):
                            description = str(module_class.DESCRIPTION)

                        version_text = None
                        if hasattr(module_class, 'VERSION'):
                            version_text = str(module_class.VERSION)

                        if hasattr(module_class, 'TICK_RATE'):
                            tick_rate = parse_interval_text(module_class.TICK_RATE)

                            if tick_rate is not None and tick_rate < 0:
                                if tick_rate == -1:
                                    LOG.warning(f'disqualifying {module_name}.{class_name}: '
                                                f'tick rate does not match regex "{INTERVAL_PATTERN.pattern}"')
                                elif tick_rate == -2:
                                    LOG.warning(f'disqualifying {module_name}.{class_name}: '
                                                f'tick rate must be positive, zero or None.')
                                elif tick_rate == -3:
                                    LOG.warning(f'disqualifying {module_name}.{class_name}: '
                                                f'failed to parse tick rate.')
                                elif tick_rate == -4:
                                    LOG.warning(f'disqualifying {module_name}.{class_name}: '
                                                f'unknown tick rate multiplier.')
                                continue
                        else:
                            LOG.warning(f'disqualifying {module_name}.{class_name}: '
                                        f'"TICK_RATE" property required')
                            continue

                        option_definitions = []
                        if hasattr(module_class, 'OPTIONS'):
                            if isinstance(module_class.OPTIONS, list):
                                option_definitions = module_class.OPTIONS
                            else:
                                LOG.warning(f'disqualifying {module_name}.{class_name}: '
                                            f'"OPTIONS" property is not a list')
                                continue

                        pluggram_metas.append(PluggramMeta(loaded_module,
                                                           module_path,
                                                           module_class,
                                                           tick_rate,
                                                           module_name,
                                                           class_name,
                                                           display_name,
                                                           description,
                                                           version_text,
                                                           positional_count,
                                                           options=option_definitions))

                        LOG.info(f'loaded pluggram {class_name} ("{module_path}")')

    return pluggram_metas


class PluggramRunner:

    @property
    def meta(self):
        return self._meta

    @property
    def running(self):
        return self._meta is not None and self._thread is not None and self._thread.is_alive()

    def __init__(self):
        self._thread = None
        self._meta = None
        self._event_stop = Event()

    def _worker(self):
        rate = self._meta.tick_rate
        marker = -rate
        while True:
            if (rate is not None and timing_counter() - marker > rate) or rate is None:
                marker = timing_counter()
                try:
                    self._meta.tick()
                except Exception as e:
                    LOG.error(f'exception while ticking pluggram "{self._meta.name}": {str(e)}')
                    LOG.error(traceback.format_exc())
            if self._event_stop.is_set():
                break

    def start(self, meta: PluggramMeta, *args, **kwargs) -> bool:
        self.stop()
        self._event_stop.clear()

        try:
            meta.init(*args, **kwargs)
        except Exception as e:
            LOG.error(
                f'exception {e.__class__.__name__} initializing pluggram "{meta.name}" ({meta.class_name}): {str(e)}')
            LOG.error(traceback.format_exc())
            return False

        self._meta = meta
        self._thread = threading.Thread(target=self._worker)
        self._thread.start()

        return True

    def stop(self):
        if self.running:
            self._event_stop.set()
            self._thread.join()
            self._meta = None
            return True
        return False


runner = PluggramRunner()
