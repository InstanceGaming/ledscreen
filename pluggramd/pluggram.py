import json
import os
import logging
import importlib.util
import traceback
import traceback as tb
import inspect
import re
import zmq
import rpc
from collections import KeysView
from multiprocessing import Event, Process
from inspect import Parameter
from typing import Optional, List, Tuple
from tinyrpc import RPCClient
from tinyrpc.protocols.msgpackrpc import MSGPACKRPCProtocol
from tinyrpc.transports.zmq import ZmqClientTransport
from rpc import InputMethod
from utils import timing_counter, configure_logger

LOG = logging.getLogger('pluggramd')
configure_logger(LOG)
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

    def get_filled_options(self):
        filled = {}
        for opt in self._options:
            key = opt.key
            filled.update({key: opt.value})
        return filled


class Pluggram:

    def tick(self):
        raise NotImplementedError('tick() was never overridden')


def load_type(module_path: str) -> Tuple[str, type]:
    """
    Get the first class name and type in the specified Python module that inherits the Pluggram type.
    Will raise TypeError if no suitable class type was found.
    """
    module_class = None
    module_name = os.path.basename(module_path)
    for file in os.listdir(module_path):
        if file == '__init__.py':
            init_path = os.path.join(module_path, file)
            LOG.debug(f'load_type("{module_path}"): found module {module_name}')

            spec = importlib.util.spec_from_file_location(module_name, init_path)
            loaded_module = importlib.util.module_from_spec(spec)

            try:
                spec.loader.exec_module(loaded_module)
            except Exception as e:
                message = f'load_type("{module_path}"): exception raised in "{file}":\n'
                message += ''.join(tb.format_exception(None, e, e.__traceback__))
                LOG.debug(message)
                LOG.warning(f'{module_name} failed to load')
                continue

            # 1. get class definitions in module to find entrypoint
            class_members = inspect.getmembers(loaded_module, inspect.isclass)

            # 2. find one class which inherits Pluggram or DQ
            class_name = None
            for class_name, module_class in class_members:
                bases = module_class.__bases__

                if Pluggram in bases:
                    break

            return class_name, module_class
    raise TypeError()


def load_one(module_path: str, argument_count: int) -> Optional[PluggramMetadata]:
    meta = None
    module_name = os.path.basename(module_path)
    for file in os.listdir(module_path):
        if file == '__init__.py':
            class_name, module_class = load_type(module_path)

            if module_class is None:
                LOG.debug(f'load_one("{module_path}", {argument_count}): '
                          'module does not define a class inheriting Pluggram')
                continue

            # 3. ensure the class has a constructor and tick()
            init_func = getattr(module_class, '__init__', None)

            if not callable(init_func):
                LOG.debug(f'load_one("{module_path}", {argument_count}): does not define constructor')
                continue

            tick_func = getattr(module_class, 'tick', None)

            if not callable(tick_func):
                LOG.debug(f'load_one("{module_path}", {argument_count}): does not define tick() method')
                continue

            # 4. note argument count
            construct_parameters = inspect.signature(module_class.__init__).parameters
            positional_count = 0

            for parameter in construct_parameters.values():
                if parameter.name != 'self':
                    if parameter.kind == Parameter.POSITIONAL_ONLY and parameter.default == Parameter.empty:
                        positional_count += 1

            if positional_count > argument_count:
                LOG.debug(f'load_one("{module_path}", {argument_count}): '
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
                        LOG.debug(f'load_one("{module_path}", {argument_count}): '
                                  f'tick rate does not match regex "{INTERVAL_PATTERN.pattern}"')
                    elif tick_rate == -2:
                        LOG.debug(f'load_one("{module_path}", {argument_count}): '
                                  f'tick rate must be positive, zero or None.')
                    elif tick_rate == -3:
                        LOG.debug(f'load_one("{module_path}", {argument_count}): '
                                  f'failed to parse tick rate.')
                    elif tick_rate == -4:
                        LOG.debug(f'load_one("{module_path}", {argument_count}): '
                                  f'unknown tick rate multiplier.')
                    continue
            else:
                LOG.debug(f'load_one("{module_path}", {argument_count}): '
                          f'"TICK_RATE" property required')
                continue

            option_definitions = []
            if hasattr(module_class, 'OPTIONS'):
                if isinstance(module_class.OPTIONS, list):
                    option_definitions = module_class.OPTIONS
                else:
                    LOG.debug(f'load_one("{module_path}", {argument_count}): '
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

            LOG.debug(f'load_one("{module_path}", {argument_count}): loaded pluggram {class_name}')
            break

    return meta


def load(programs_dir: str, argument_count):
    if not os.path.isdir(programs_dir):
        raise RuntimeError('Programs directory does not exist or is not a directory')

    pluggram_metas = []

    for _, dirs, _ in os.walk(programs_dir, topdown=True, followlinks=False):
        for module_name in dirs:
            module_path = os.path.abspath(os.path.join(programs_dir, module_name))
            if os.path.exists(module_path):
                meta = load_one(module_path, argument_count)
                pluggram_metas.append(meta)

    return pluggram_metas


def pluggram_process(module_path: str,
                     module_name: str,
                     screen_url: str,
                     tick_rate: Optional[int],
                     filled_options: dict,
                     stop_event: Event):
    abort = False
    try:
        klass_name, live_type = load_type(module_path)
    except TypeError:
        LOG.error('failed to get module class type, try restarting')
        abort = True

    if not abort:
        # start screen RPC client
        context = zmq.Context()
        screen_client = RPCClient(
            MSGPACKRPCProtocol(),
            ZmqClientTransport.create(context, screen_url)
        )
        screen_proxy = screen_client.get_proxy()
        screen = rpc.Screen(screen_proxy)

        try:
            instance = live_type(screen, **filled_options)
        except Exception as e:
            LOG.error(
                f'exception {e.__class__.__name__} initializing pluggram "{module_name}": {str(e)}')
            LOG.error(traceback.format_exc())
            abort = True

        if not abort:
            marker = -tick_rate
            while True:
                if (tick_rate is not None and timing_counter() - marker > tick_rate) or tick_rate is None:
                    marker = timing_counter()
                    try:
                        instance.tick()
                    except Exception as e:
                        LOG.error(f'exception while ticking pluggram "{module_name}": {str(e)}')
                        LOG.error(traceback.format_exc())
                        stop_event.set()
                if stop_event.is_set():
                    break


class PluggramRunner:

    @property
    def meta(self):
        return self._meta

    @property
    def is_running(self):
        return self._meta is not None and self._proc is not None and self._proc.is_alive()

    @property
    def running(self) -> Optional[PluggramMetadata]:
        return self._meta

    def __init__(self):
        self._proc = None
        self._meta = None
        self._event_stop = Event()

    def start(self, meta: PluggramMetadata, screen_url: str):
        self.stop()
        self._event_stop.clear()
        self._meta = meta
        filled_options = meta.get_filled_options()

        LOG.info(f'starting pluggram worker for program {self._meta.name}')
        self._proc = Process(target=pluggram_process, args=(meta.module_path,
                                                            meta.name,
                                                            screen_url,
                                                            meta.tick_rate,
                                                            filled_options,
                                                            self._event_stop))
        self._proc.start()
        LOG.info(f'started pluggram worker for program {self._meta.name}')

    def stop(self):
        LOG.info('stopping pluggram worker')
        if self.is_running:
            self._event_stop.set()
            self._proc.join()
            self._meta = None
            LOG.info('stopped pluggram worker')
            return True
        return False
