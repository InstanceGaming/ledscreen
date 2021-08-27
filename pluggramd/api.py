from typing import List, Tuple, Union, Optional
from pluggram import PluggramRunner, PluggramMetadata
from functools import lru_cache
from tinyrpc.dispatch import public


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
    def get_info(self, name: str) -> Optional[Tuple[str,
                                                    Optional[str],
                                                    Optional[str],
                                                    Optional[int]]]:
        m = self._find_by_name(name)
        return m.display_name, m.description, m.version, m.tick_rate

    @public
    def get_options(self, name: str) -> List[Tuple[str,
                                                   str,
                                                   List,
                                                   Optional[Union[int, float]],
                                                   Optional[Union[int, float]],
                                                   Union[int, float, bool, str],
                                                   Optional[Union[int, float,
                                                                  bool, str]],
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
    def save_options(self, name: str, options: dict) -> Tuple[List[str],
                                                              List[str]]:
        m = self._find_by_name(name)
        return m.save_options(options)

    @public
    def get_running(self) -> Optional[str]:
        if self._runner.is_running:
            return self._runner.running.name
        return None

    @public
    def start(self, name: str) -> bool:
        metadata = self._find_by_name(name)
        running_name = self.get_running()
        if running_name is None or metadata.name != running_name:
            self._runner.start(metadata, self._screen_url)
            return True
        else:
            return False

    @public
    def stop(self) -> bool:
        return self._runner.stop()
