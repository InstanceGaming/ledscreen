from typing import List, Tuple, Union, Optional
from tinyrpc.dispatch import public
from pluggram import PluggramMetadata
from rpc import Screen, Option, PluggramInfo
from functools import lru_cache


class PluggramManager:

    def __init__(self, metadata: List[PluggramMetadata], screen: Screen):
        self._metadata = metadata
        self._screen = screen

    @lru_cache(maxsize=10)
    def _find_by_name(self, name: str) -> PluggramMetadata:
        for m in self._metadata:
            if m.name == name:
                return m
        else:
            raise KeyError('Program not found')

    @public
    def get_names(self) -> List[str]:
        return [m.name for m in self._metadata]

    @public
    def get_options(self, name: str) -> List[Tuple[str,
                                                   str,
                                                   List,
                                                   Optional[Union[int, float]],
                                                   Optional[Union[int, float]],
                                                   Union[int, float, bool, str],
                                                   Optional[Union[int, float, bool, str]],
                                                   Optional[str],
                                                   int]]:
        metadata = self._find_by_name(name)
        data = []

        for opt in metadata.options:
            data.append((opt.key,
                         opt.type_name,
                         opt.choices,
                         opt.min,
                         opt.max,
                         opt.default,
                         opt.value,
                         opt.help_text,
                         opt.input_method))

        return data

    @public
    def save_options(self, name: str, options: dict) -> Tuple[List[str], bool]:
        return [], False

    @public
    def get_running(self) -> Optional[str]:
        return None

    @public
    def start(self, name: str) -> bool:
        return False

    @public
    def stop(self):
        pass
