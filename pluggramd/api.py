from typing import List, Tuple, Union, Optional
from tinyrpc.dispatch import public
from pluggram import PluggramMetadata, PluggramRunner
from functools import lru_cache


class PluggramManager:

    def __init__(self,
                 metadata: List[PluggramMetadata],
                 screen_url: str):
        self._metadata = metadata
        self._screen_url = screen_url
        self._runner = PluggramRunner()

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
        if self._runner.is_running:
            return self._runner.running.name
        return None

    @public
    def start(self, name: str):
        metadata = self._find_by_name(name)
        self._runner.start(metadata, self._screen_url)

    @public
    def stop(self) -> bool:
        return self._runner.stop()
