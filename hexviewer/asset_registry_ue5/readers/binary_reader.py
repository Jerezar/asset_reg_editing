import io
import os
import struct
import sys

from hexviewer.asset_registry_ue5.bytes import BITMASK_16, BITMASK_32
from hexviewer.asset_registry_ue5.unreal_types import FGuid, SerializedString, TagMapHandle, FValueID


class BinaryReader:
    stream: io.BytesIO

    def __init__(self, stream: io.BytesIO, file_byte_order = sys.byteorder):
        self.stream = stream

        self.read_bytes = stream.read
        self.tell = stream.tell
        self.seek = stream.seek

        self.seek(0, os.SEEK_END)
        self.byte_size = self.tell()
        self.seek(0)

        self.file_byte_order = file_byte_order

    def read_int8(self):
        return int.from_bytes(self.stream.read(1), signed=True, byteorder=self.file_byte_order)
    def read_uint8(self):
        return int.from_bytes(self.stream.read(1), signed=False, byteorder=self.file_byte_order)

    def read_int16(self):
        return int.from_bytes(self.stream.read(2), signed=True, byteorder=self.file_byte_order)
    def read_uint16(self):
        return int.from_bytes(self.stream.read(2), signed=False, byteorder=self.file_byte_order)

    def read_int32(self):
        return int.from_bytes(self.stream.read(4), signed=True, byteorder=self.file_byte_order)
    def read_uint32(self):
        return int.from_bytes(self.stream.read(4), signed=False, byteorder=self.file_byte_order)

    def read_int64(self):
        return int.from_bytes(self.stream.read(8), signed=True, byteorder=self.file_byte_order)
    def read_uint64(self):
        return int.from_bytes(self.stream.read(8), signed=False, byteorder=self.file_byte_order)

    def read_float32(self):
        f_bytes = self.stream.read(4)
        if self.file_byte_order == "big":
            f_bytes = reversed(f_bytes)
        return struct.unpack("f", f_bytes)

    def read_float64(self):
        f_bytes = self.stream.read(8)
        if self.file_byte_order == "big":
            f_bytes = reversed(f_bytes)
        return struct.unpack("d", f_bytes)

    def read_bool(self):
        return bool(self.read_int32())

    def read_guid(self) -> FGuid:
        guid = (
            self.read_uint32(),
            self.read_uint32(),
            self.read_uint32(),
            self.read_uint32(),
        )

        return guid

    def read_fstring(self):
        is_wide = False
        char_len = self.read_int32()  # size is with null terminator

        if char_len < 0:
            char_len *= -1
            is_wide = True

        string_data = self.read_bytes(char_len * (2 if is_wide else 1))

        return SerializedString(string_data, is_wide)

    def read_value_id(self):
        data = self.read_uint32()
        return FValueID(
            value_type=((data << FValueID.INDEX_BITS)&BITMASK_32)>>FValueID.INDEX_BITS,
            value_index=data >> FValueID.TYPE_BITS,
        )

    def read_tag_map_handle(self):
        data = self.read_uint64()
        return TagMapHandle(
            has_numberless_keys=bool(data >> 63),
            handle_num=(data >> 32) & BITMASK_16,
            pair_begin=data & BITMASK_32
        )

    def read_serialized_fname(self):
        is_wide = self.read_bool()
        string_data = self.read_bytes(2048)
        non_case_preserving_hash = self.read_uint16()
        case_preserving_hash = self.read_uint16()

        return SerializedString(
            string_data,
            is_wide
        )



