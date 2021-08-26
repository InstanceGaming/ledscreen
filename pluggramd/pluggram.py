import json
import os
import logging
import importlib.util
import traceback
import traceback as tb
import inspect
import re
from collections import KeysView
from multiprocessing import Event, Process
from inspect import Parameter
from typing import Optional, List

from rpc import InputMethod
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


class PluggramMetadata:

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
    def options(self) -> List[Option]:
        return self._options
    
    @property
    def tick_rate(self):
        return self._tick_rate

    @property
    def positional_count(self):
        return self._positional_count

    @property
    def has_user_options(self):
        return os.path.exists(self._store_path)

    @property
    def initialized(self):
        return self._initialized

    def __init__(self,
                 module_path: str,
                 tick_rate: Optional[int],
                 name: str,
                 class_name: str,
                 display_name: str,
                 description: str,
                 version: str,
                 positional_count: int,
                 options=None):
        self._path = module_path
        self._class_name = class_name
        self._tick_rate = tick_rate
        self._name = name
        self._display_name = display_name
        self._description = description
        self._version = version
        self._positional_count = positional_count
        self._options = options or []
        self._store_path = os.path.join(self.module_path, USER_OPTIONS_FILE)
        self._initialized = False

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

    def init(self, live_type: type, *args, **kwargs) -> type:
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

        self._initialized = True
        return live_type(*args, **options)


class Pluggram:

    def tick(self):
        raise NotImplementedError('tick() was never overridden')


def load_one(module_path: str, module_name: str, argument_count: int):
    meta = None
    module_class = None
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

            meta = PluggramMetadata(module_path,
                                    tick_rate,
                                    module_name,
                                    class_name,
                                    display_name,
                                    description,
                                    version_text,
                                    positional_count,
                                    options=option_definitions)

            LOG.info(f'loaded pluggram {class_name} ("{module_path}")')
            break

    return meta, module_class


def load(programs_dir: str, argument_count):
    if not os.path.isdir(programs_dir):
        raise RuntimeError('Programs directory does not exist or is not a directory')

    pluggram_metas = []
    pluggram_classes = []

    for _, dirs, _ in os.walk(programs_dir, topdown=True, followlinks=False):
        for module_name in dirs:
            module_path = os.path.abspath(os.path.join(programs_dir, module_name))
            if os.path.exists(module_path):
                meta, klass = load_one(module_path, module_name, argument_count)
                pluggram_metas.append(meta)
                pluggram_classes.append(klass)

    return pluggram_metas, pluggram_classes


def _worker(meta: PluggramMetadata,
            args: list,
            kwargs: dict,
            stop_event: Event):
    _, live_type = load_one(meta.module_path, meta.name, meta.positional_count)

    try:
        instance = meta.init(live_type, *args, **kwargs)
    except Exception as e:
        LOG.error(
            f'exception {e.__class__.__name__} initializing pluggram "{meta.name}" ({meta.class_name}): {str(e)}')
        LOG.error(traceback.format_exc())
        return

    rate = meta.tick_rate
    marker = -rate
    while True:
        if (rate is not None and timing_counter() - marker > rate) or rate is None:
            marker = timing_counter()
            try:
                instance.tick()
            except Exception as e:
                LOG.error(f'exception while ticking pluggram "{meta.name}": {str(e)}')
                LOG.error(traceback.format_exc())
                stop_event.set()
        if stop_event.is_set():
            break


class PluggramRunner:

    @property
    def meta(self):
        return self._meta

    @property
    def running(self):
        return self._meta is not None and self._proc is not None and self._proc.is_alive()

    def __init__(self):
        self._proc = None
        self._meta = None
        self._event_stop = Event()

    def start(self, meta: PluggramMetadata, *args, **kwargs) -> bool:
        self.stop()
        self._event_stop.clear()
        self._meta = meta

        LOG.info(f'starting pluggram worker for program {self._meta.name}')
        self._proc = Process(target=_worker, args=(self._meta,
                                                   args,
                                                   kwargs,
                                                   self._event_stop))
        self._proc.start()
        LOG.info(f'started pluggram worker for program {self._meta.name}')

        return True

    def stop(self):
        LOG.info('stopping pluggram worker')
        if self.running:
            self._event_stop.set()
            self._proc.join()
            self._meta = None
            LOG.info('stopped pluggram worker')
            return True
        return False


runner = PluggramRunner()
