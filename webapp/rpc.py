from typing import Tuple, Optional, List, Union
from dataclasses import dataclass
from enum import IntFlag
from functools import lru_cache

import utils


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
              data: bytes,
              box=None,
              update_painter=False):
        self._rpc.paste(data, box, update_painter)

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
        return self._rpc.text_dimensions(message, spacing, features, stroke_width)

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
        self._rpc.draw_text(x, y, color, message, anchor, spacing, alignment, stroke_width, stroke_fill)

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
    value: Optional[Union[int, float, bool, str]]
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
    @lru_cache
    def display_name(self):
        return utils.get_key_display_name(self.name)

    @property
    @lru_cache
    def markup_id(self):
        return self.name.replace('_', '-').lower()


@dataclass(frozen=True)
class PluggramInfo:
    display_name: str
    version: Optional[str]
    description: Optional[str]


class PluggramManager:

    def __init__(self, rpc_proxy):
        self._rpc = rpc_proxy

    @lru_cache
    def get_names(self) -> List[str]:
        return self._rpc.get_names()

    @lru_cache(maxsize=10)
    def get_info(self, name: str) -> Optional[PluggramInfo]:
        return self._rpc.get_info(name)

    @lru_cache(maxsize=10)
    def get_options(self, name: str) -> List[Option]:
        options = []
        flat_options = self._rpc.get_options(name)

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
            options.append(Option(name, type_name, choices, min_val, max_val, default, value, help_text, input_method))

        return options

    def save_options(self, name: str, options: dict) -> Tuple[List[str], bool]:
        return self._rpc.save_options(name, options)

    def get_running(self) -> Optional[str]:
        return self._rpc.get_running()

    def start(self, name: str):
        self._rpc.start(name)

    def stop(self) -> bool:
        return self._rpc.stop()
