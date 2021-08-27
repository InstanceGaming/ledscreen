import time
import os
import logging

LOG = logging.getLogger('ledscreen.utils')
DEV_FORMATTER = logging.Formatter('{levelname:>8}: {message} [{name}@{lineno}]',
                                  datefmt='%x %H:%M:%S',
                                  style='{')
FORMATTER = logging.Formatter('{levelname:>8}: {message}', style='{')


def configure_logger(log, prod_level=logging.INFO):
    handler = logging.StreamHandler()

    # noinspection PyUnreachableCode
    if __debug__:
        log.setLevel(logging.DEBUG)
        handler.setFormatter(DEV_FORMATTER)
    else:
        log.setLevel(logging.INFO)
        handler.setFormatter(FORMATTER)

    log.handlers.clear()
    log.addHandler(handler)


def combine_rgb(r: int, g: int, b: int):
    return (r << 16) | (g << 8) | b


def pretty_timedelta(td, prefix=None, format_spec=None):
    prefix = prefix or ''
    format_spec = format_spec or '02.2f'

    if td is not None:
        seconds = td.total_seconds()
        if seconds < 60:
            return prefix + format(seconds, format_spec) + ' sec'
        elif 60 <= seconds < 3600:
            return prefix + format(seconds / 60, format_spec) + ' min'
        elif 3600 <= seconds < 86400:
            return prefix + format(seconds / 3600, format_spec) + ' hr'
        elif 86400 <= seconds:
            return prefix + format(seconds / 86400, format_spec) + ' days'
    return None


def get_key_display_name(key: str):
    return key.replace('_', ' ').capitalize()


def canonical_filename(directory: str, name: str):
    for file in os.listdir(directory):
        if file.lower().strip() == name.lower().strip():
            return file
    return None


def timing_counter():
    """
    perf_counter() in milliseconds.
    """
    return time.perf_counter() * 1000
