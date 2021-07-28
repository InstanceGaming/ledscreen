from enum import IntEnum


ENDIANNESS = 'big'
TEXT_ENCODING = 'utf-16'


def int_to_bytes(value: int, length: int, signed=False) -> bytes:
    return value.to_bytes(length, byteorder=ENDIANNESS, signed=signed)


def int_from_bytes(b: bytes, length: int, signed=False) -> int:
    if len(b) != length:
        raise ValueError(f'input bytes different size than expected ({len(b)} instead of {length})')

    return int.from_bytes(b, byteorder=ENDIANNESS, signed=signed)


class DecodeError(IntEnum):
    EMPTY = 1
    BAD_HEADER = 2
    LENGTH = 3
    PARSE_FAIL = 4
    UNKNOWN_TYPE = 5


class StandardFrame(IntEnum):
    AWK = 1
    NAK = 2
    ERR = 3
    SCREEN_INFO = 10
    RENDER = 20
    SET_PIXEL = 21
    CLEAR = 22
    FILL = 23
    LOAD_FONT = 24
    DRAW_TEXT = 25
    DRAW_POLY = 26
    DRAW_ELPS = 27
    FILL_IMAGE = 28
    PLAY_VIDEO = 29
    UNKNOWN = 255


class StandardError(IntEnum):
    UNKNOWN_FONT = 1
    OUT_OF_BOUNDS = 2


def decode(b: bytes):
    frame_length = len(b)
    data = None
    frame_type = StandardFrame.UNKNOWN
    error = None

    if frame_length > 0:
        header_byte = b[0]

        try:
            frame_type = StandardFrame(header_byte)
        except ValueError:
            error = DecodeError.BAD_HEADER

        if frame_length > 1:
            payload = b[1:]
            payload_length = len(payload)

            if frame_type == StandardFrame.ERR:
                if payload_length < 1:
                    error = DecodeError.LENGTH
                else:
                    try:
                        unicode_text = payload[2:].decode(TEXT_ENCODING)
                        data = [
                            payload[0],
                            unicode_text
                        ]
                    except UnicodeDecodeError:
                        error = DecodeError.PARSE_FAIL
            elif frame_type == StandardFrame.FILL:
                if payload_length != 3:
                    error = DecodeError.LENGTH
                else:
                    try:
                        data = int_from_bytes(payload, 3)
                    except ValueError:
                        error = DecodeError.PARSE_FAIL
            elif frame_type == StandardFrame.SET_PIXEL:
                if payload_length != 5:
                    error = DecodeError.LENGTH
                else:
                    try:
                        data = [
                            int_from_bytes(payload[:2], 2),
                            int_from_bytes(payload[2:], 3)
                        ]
                    except ValueError:
                        error = DecodeError.PARSE_FAIL
            else:
                error = DecodeError.UNKNOWN_TYPE
    else:
        error = DecodeError.EMPTY

    return data, frame_type, error


class AwkFrame:
    STANDARD = StandardFrame.AWK

    @staticmethod
    def encode() -> bytes:
        return int_to_bytes(AwkFrame.STANDARD, 1)


class NakFrame:
    STANDARD = StandardFrame.NAK

    @staticmethod
    def encode() -> bytes:
        return int_to_bytes(NakFrame.STANDARD, 1)


class ErrFrame:
    STANDARD = StandardFrame.ERR

    @staticmethod
    def encode(code: StandardError, message: str) -> bytes:
        return int_to_bytes(ErrFrame.STANDARD, 1) + int_to_bytes(code, 1) + message.encode(TEXT_ENCODING)


class ClearFrame:
    STANDARD = StandardFrame.CLEAR

    @staticmethod
    def encode() -> bytes:
        return int_to_bytes(ClearFrame.STANDARD, 1)


class FillFrame:
    STANDARD = StandardFrame.FILL

    @staticmethod
    def encode(color: int) -> bytes:
        return int_to_bytes(FillFrame.STANDARD, 1) + int_to_bytes(color, 3)


class RenderFrame:
    STANDARD = StandardFrame.RENDER

    @staticmethod
    def encode() -> bytes:
        return int_to_bytes(RenderFrame.STANDARD, 1)


class LoadFontFrame:
    STANDARD = StandardFrame.LOAD_FONT

    @staticmethod
    def encode(name: str) -> bytes:
        raise NotImplementedError()


class DrawTextFrame:
    STANDARD = StandardFrame.DRAW_TEXT

    @staticmethod
    def encode(index: int,
               text: str,
               color: int,
               background,
               size: int,
               bold=False,
               italic=False) -> bytes:
        raise NotImplementedError()


class DrawPolygonFrame:
    STANDARD = StandardFrame.DRAW_POLY

    @staticmethod
    def encode(start_index: int,
               end_index: int,
               color: int,
               aliasing=False) -> bytes:
        raise NotImplementedError()


class DrawElipseFrame:
    STANDARD = StandardFrame.DRAW_ELPS

    @staticmethod
    def encode(a_index: int,
               b_index: int,
               radius: int,
               color: int,
               stroke_width: int,
               stroke_color=None) -> bytes:
        raise NotImplementedError()


class SetPixelFrame:
    STANDARD = StandardFrame.SET_PIXEL

    @staticmethod
    def encode(index: int,
               color: int) -> bytes:
        return int_to_bytes(SetPixelFrame.STANDARD, 1) + int_to_bytes(index, 2) + int_to_bytes(color, 3)


class ScreenInfoFrame:
    STANDARD = StandardFrame.SCREEN_INFO

    @staticmethod
    def encode(width: int, height: int) -> bytes:
        return int_to_bytes(ScreenInfoFrame.STANDARD, 1) + int_to_bytes(width, 2) + int_to_bytes(height, 2)
