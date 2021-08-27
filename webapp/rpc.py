import io
import utils
from enum import IntFlag
from typing import List, Tuple, Union, Optional
from functools import lru_cache
from PIL.Image import Image
from threading import Lock
from dataclasses import dataclass


class Screen:

    @property
    def width(self) -> int:
        return self._rpc.width()

    @property
    def height(self) -> int:
        return self._rpc.height()

    @property
    def pixel_count(self) -> int:
        return self._rpc.pixel_count()

    @property
    def center(self) -> Tuple[int, int]:
        return self._rpc.center()

    @property
    def antialiasing(self) -> bool:
        return self._rpc.antialiasing()

    @antialiasing.setter
    def antialiasing(self, v):
        self._rpc.set_antialiasing(v)

    @property
    def current_font(self) -> Tuple[str, str]:
        return self._rpc.current_font()

    @property
    def max_brightness(self) -> int:
        return self._rpc.max_brightness()

    def __init__(self, rpc_proxy):
        self._rpc = rpc_proxy

    def paste(self,
              img: Image,
              box=None,
              fmt='png'):
        output = io.BytesIO()
        img.save(output, format=fmt)
        self._rpc.paste(output.getvalue(), box)

    def render(self):
        self._rpc.render()

    def set_pixel(self,
                  x: int,
                  y: int,
                  color: int):
        self._rpc.set_pixel(x, y, color)

    def set_brightness(self,
                       v: int):
        self._rpc.set_brightness(v)

    def set_font(self,
                 name: str,
                 size=None,
                 font_face=None) -> bool:
        return self._rpc.set_font(name, size, font_face)

    def font_names(self) -> list:
        return self._rpc.font_names()

    def text_dimensions(self,
                        message: str,
                        spacing=None,
                        features=None,
                        stroke_width=None) -> Tuple[int, int]:
        return self._rpc.text_dimensions(message,
                                         spacing,
                                         features,
                                         stroke_width)

    def index_of(self,
                 x: int,
                 y: int) -> int:
        return self._rpc.index_of(x, y)

    def draw_text(self,
                  x: int,
                  y: int,
                  color: int,
                  message: str,
                  anchor=None,
                  spacing=None,
                  alignment=None,
                  stroke_width=None,
                  stroke_fill=None):
        self._rpc.draw_text(x,
                            y,
                            color,
                            message,
                            anchor,
                            spacing,
                            alignment,
                            stroke_width,
                            stroke_fill)

    def fill(self,
             color: int,
             box=None):
        self._rpc.fill(color, box)

    def draw_ellipse(self,
                     x: int,
                     y: int,
                     width=None,
                     color=None,
                     outline=None):
        self._rpc.draw_ellipse(x, y, width, color, outline)

    def draw_line(self,
                  x: int,
                  y: int,
                  color=None,
                  width=None,
                  rounded=False):
        self._rpc.draw_line(x, y, color, width, rounded)

    def clear(self):
        self._rpc.clear()

    def write_file(self,
                   filename: str):
        self._rpc.write_file(filename)

    def get_data(self):
        return self._rpc.get_data()

    def reset_frame_count(self):
        self._rpc.reset_frame_count()


class InputMethod(IntFlag):
    DEFAULT = 0b00000000
    COLOR_PICKER = 0b00000001


@dataclass(frozen=True)
class Option:
    name: str
    type_name: str
    default: Union[int, float, bool, str]
    input_method: InputMethod
    choices: Optional[List[str]]
    min: Optional[Union[int, float]]
    max: Optional[Union[int, float]]
    value: Union[int, float, bool, str]
    help_text: Optional[str]

    @property
    def type(self) -> type:
        if self.type_name == 'INT':
            return int
        elif self.type_name == 'FLOAT':
            return float
        elif self.type_name == 'BOOL':
            return bool
        elif self.type_name == 'STR':
            return str
        else:
            raise NotImplementedError()

    @property
    def display_name(self):
        return utils.get_key_display_name(self.name)

    @property
    def markup_id(self):
        return self.name.replace('_', '-').lower()

    @property
    def rgb_color(self):
        if self.type_name == 'INT':
            bgr = self.value
            r = bgr & 0xFF
            g = (bgr >> 8) & 0xFF
            b = (bgr >> 16) & 0xFF
            return (r << 16) | (g << 8) | b
        return None


@dataclass(frozen=True)
class PluggramInfo:
    name: str
    display_name: str
    description: Optional[str]
    version: Optional[str]
    tick_rate: Optional[int]
    options: Optional[List[Option]]


class PluggramManager:

    def __init__(self, rpc_proxy):
        self._rpc = rpc_proxy
        self._lk: Lock = Lock()

    def _lock(self):
        self._lk.acquire(timeout=2)

    def _unlock(self):
        self._lk.release()

    @lru_cache
    def get_names(self) -> List[str]:
        self._lock()
        rv = self._rpc.get_names()
        self._unlock()
        return rv

    @lru_cache(maxsize=10)
    def get_info(self, name: str, options=False) -> Optional[PluggramInfo]:
        self._lock()
        display_name, description, version, tick_rate = self._rpc.get_info(name)
        self._unlock()

        if not options:
            return PluggramInfo(name,
                                display_name,
                                description,
                                version,
                                tick_rate,
                                None)
        else:
            opts = self.get_options(name)
            return PluggramInfo(name,
                                display_name,
                                description,
                                version,
                                tick_rate,
                                opts)

    def get_options(self, name: str) -> List[Option]:
        options = []
        self._lock()
        flat_options = self._rpc.get_options(name)
        self._unlock()

        for flat_option in flat_options:
            name = flat_option[0]
            type_name = flat_option[1]
            choices = flat_option[2]
            min_val = flat_option[3]
            max_val = flat_option[4]
            default = flat_option[5]
            value = flat_option[6]
            help_text = flat_option[7]
            input_type = flat_option[8]
            input_method = InputMethod(input_type)
            options.append(Option(name,
                                  type_name,
                                  default,
                                  input_method,
                                  choices,
                                  min_val,
                                  max_val,
                                  value,
                                  help_text))

        return options

    def save_options(self, name: str, options: dict) -> Tuple[List[str],
                                                              List[str]]:
        self._lock()
        rv = self._rpc.save_options(name, options)
        self._unlock()
        return rv

    def get_running(self) -> Optional[str]:
        self._lock()
        rv = self._rpc.get_running()
        self._unlock()
        return rv

    def start(self, name: str) -> bool:
        self._lock()
        rv = self._rpc.start(name)
        self._unlock()
        return rv

    def stop(self) -> bool:
        self._lock()
        rv = self._rpc.stop()
        self._unlock()
        return rv
