import io
import struct
import sys

from hexviewer.asset_registry_ue5.bytes import BITMASK_16, BITMASK_32
from hexviewer.asset_registry_ue5.unreal_types import FGuid, SerializedString, TagMapHandle, FValueID
from hexviewer.asset_registry_ue5.utils import encode_no_bom


class BinaryWriter:
    stream: io.BytesIO

    def __init__(self, stream: io.BytesIO, file_byte_order = sys.byteorder):
        self.stream = stream

        self.write_bytes = stream.write
        self.tell = stream.tell
        self.seek = stream.seek

        self.file_byte_order = file_byte_order

    def write_int8(self, val: int):
        self.stream.write(val.to_bytes(1, signed=True, byteorder=self.file_byte_order))
    def write_uint8(self, val: int):
        self.stream.write(val.to_bytes(1, signed=False, byteorder=self.file_byte_order))

    def write_int16(self, val: int):
        self.stream.write(val.to_bytes(2, signed=True, byteorder=self.file_byte_order))
    def write_uint16(self, val: int):
        self.stream.write(val.to_bytes(2, signed=False, byteorder=self.file_byte_order))

    def write_int32(self, val: int):
        self.stream.write(val.to_bytes(4, signed=True, byteorder=self.file_byte_order))
    def write_uint32(self, val: int):
        self.stream.write(val.to_bytes(4, signed=False, byteorder=self.file_byte_order))

    def write_int64(self, val: int):
        self.stream.write(val.to_bytes(8, signed=True, byteorder=self.file_byte_order))
    def write_uint64(self, val: int):
        self.stream.write(val.to_bytes(8, signed=False, byteorder=self.file_byte_order))

    def write_float32(self, val):
        f_bytes = struct.pack("f", val)
        if self.file_byte_order == "big":
            f_bytes = reversed(f_bytes)
        self.stream.write(f_bytes)

    def write_float64(self, val):
        f_bytes = struct.pack("d", val)
        if self.file_byte_order == "big":
            f_bytes = reversed(f_bytes)
        self.stream.write(f_bytes)

    def write_bool(self, val):
        self.write_int32(bool(val))

    def write_guid(self, guid: FGuid):
        for part in guid:
            self.write_uint32(part)

    def write_fstring(self, val: SerializedString):
        parsed_string = val.string_view() + "\x00"

        num_chars = len(parsed_string)
        if val.is_wide:
            num_chars *= -1

        self.write_int32(num_chars)
        self.write_bytes(encode_no_bom(parsed_string, is_wide=val.is_wide))


    def write_value_id(self, val: FValueID):
        val_type = int(val.value_type)
        val_index = val.value_index << FValueID.TYPE_BITS

        self.write_uint32(val_index | val_type)

    def write_tag_map_handle(self, val: TagMapHandle):
        numberless_flag = bool(val.has_numberless_keys) << 63
        handle_num = (val.handle_num & BITMASK_16) << 32
        pair_begin = val.pair_begin & BITMASK_32

        self.write_uint64(numberless_flag | handle_num | pair_begin)

    def write_serialized_fname(self, val: SerializedString):
        parsed_string = val.string_view()

        parsed_string += (1024 - len(parsed_string)) * "\x00"

        self.write_bool(val.is_wide)
        self.write_bytes(parsed_string.encode(encoding="utf-16" if val.is_wide else "utf-8"))
        self.write_uint16(0)
        self.write_uint16(0)