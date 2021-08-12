import enum
import os
import logging
import importlib.util
import traceback
import traceback as tb
import inspect
import re
import threading
from multiprocessing import Event
from inspect import Parameter
from utils import timing_counter

LOG = logging.getLogger('ledscreen.pluggram')
INTERVAL_PATTERN = re.compile(r'(\d+)(ms|s|m)')
NAME_KEY_PATTERN = re.compile(r'(^a-z0-9_)')

RUNNING_PLUGGRAM = None
RUNNING_PLUGGRAM_META = None
RUNNING_PLUGGRAM_THREAD = None
_EXIT_EVENT = Event()


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
    SUPPORTED_TYPES = [int, str, bool]

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
        return type(self._default)

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

        if NAME_KEY_PATTERN.match(key):
            raise ValueError(f'"{key}" is invalid (matched with pattern "{NAME_KEY_PATTERN.pattern}")')

        self._default = default
        self._min = None
        self._max = None
        self._choices = None
        self._help_text = kwargs.get('help')
        self._input_method = InputMethod.DEFAULT
        self._value = None

        if self.type not in self.SUPPORTED_TYPES:
            raise TypeError(f'unsupported option type {self.type}')

        if self.type == str:
            choices = kwargs.get('choices')

            if choices is not None:
                if isinstance(choices, list):
                    if default not in choices:
                        raise ValueError('default value not present in choices')

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
                        if max_val < min_val:
                            raise ValueError('max value less than min value')

                    self._max = max_val
                else:
                    raise TypeError('max value must be an integer')

            if kwargs.get('color_picker'):
                self._input_method = InputMethod.COLOR_PICKER

    def __repr__(self):
        return f'<Option "{self._key}" {self.type_name} default={self._default}>'

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
        return isinstance(o, self.type)


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

    def init(self, *args, **kwargs):
        if len(args) < self._positional_count:
            raise RuntimeError(f'Argument mismatch (wants {self._positional_count})')

        known_keys = [o.key for o in self._options]
        for key, value in kwargs.items():
            if key in known_keys:
                known_keys.remove(key)
                for option in self._options:
                    if option.key == key:
                        valid = option.validate(value)

                        if not valid:
                            raise ValueError(f'Option "{key}" has invalid value')

                        break

        for unset_key in known_keys:
            for option in self._options:
                if option.key == unset_key:
                    default_value = option.default
                    break
            else:
                raise RuntimeError(f'Failed to find default value for unset kwarg "{unset_key}"')

            kwargs.update({unset_key: default_value})

        return self._entry_class(*args, **kwargs)


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


def _pluggram_worker(meta: PluggramMeta, instance: Pluggram):
    rate = meta.tick_rate
    marker = -rate
    while True:
        if (rate is not None and timing_counter() - marker > rate) or rate is None:
            marker = timing_counter()
            try:
                instance.tick()
            except Exception as e:
                LOG.error(f'exception while updating pluggram "{meta.name}": {str(e)}')
                LOG.error(traceback.format_exc())
        if _EXIT_EVENT.is_set():
            break


def _start_thread(pluggram: PluggramMeta):
    t = threading.Thread(target=_pluggram_worker, args=[pluggram])
    t.start()
    return t


def _stop_thread(thread: threading.Thread):
    _EXIT_EVENT.set()
    thread.join()


def start_pluggram(meta: PluggramMeta, *args):
    global RUNNING_PLUGGRAM, RUNNING_PLUGGRAM_META, RUNNING_PLUGGRAM_THREAD
    pause_pluggram()

    try:
        RUNNING_PLUGGRAM = meta.init(*args)
    except Exception as e:
        LOG.error(f'exception {e.__class__.__name__} initializing pluggram "{meta.name}" ({meta.class_name}): {str(e)}')
        LOG.error(traceback.format_exc())

    RUNNING_PLUGGRAM_THREAD = _start_thread(meta)
    RUNNING_PLUGGRAM_META = meta


def pause_pluggram():
    global RUNNING_PLUGGRAM, RUNNING_PLUGGRAM_META, RUNNING_PLUGGRAM_THREAD

    if RUNNING_PLUGGRAM_THREAD is not None:
        _stop_thread(RUNNING_PLUGGRAM_THREAD)

    RUNNING_PLUGGRAM = None
    RUNNING_PLUGGRAM_META = None
