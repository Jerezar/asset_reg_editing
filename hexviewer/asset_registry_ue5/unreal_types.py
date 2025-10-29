from dataclasses import dataclass
from typing import TypeAlias, ClassVar

from hexviewer.asset_registry_ue5.bytes import BITMASK_8
from hexviewer.asset_registry_ue5.name_pool import FNAME_POOL_SHARDS
from hexviewer.asset_registry_ue5.tag_value_types import ValueTypes


@dataclass
class SerializedString:
    string_data: bytes
    is_wide: bool

    def string_view(self):
        return self.string_data.decode("utf-16" if self.is_wide else "utf-8").rstrip("\x00")

    @classmethod
    def from_string(cls, val: str):
        is_wide = not val.isascii()
        string_data = val.encode("utf-16" if is_wide else "utf-8")
        return cls(string_data=string_data, is_wide=is_wide)

LITERAL_NONE = "NONE" #0x454e4f4e  if sys.byteorder == "little" else 0x4e4f4e45

# every lowercase character has 2^5 bit set; setting it off subtracts 32 and thus converting
# lowercase into uppercase, without changing uppercase characters
# TO_UPPER_MASK = 0xdfdfdfdf



FNAME_MAX_BLOCK_BITS = 13
FNAME_BLOCK_OFFSET_BITS = 16
FNAME_MAX_BLOCKS = 1 << FNAME_MAX_BLOCK_BITS
FNAME_BLOCK_OFFSETS = 1 << FNAME_BLOCK_OFFSET_BITS

#slot
FNAME_ENTRY_IDBITS = FNAME_BLOCK_OFFSET_BITS + FNAME_MAX_BLOCK_BITS
FNAME_ENTRY_IDMASK = (1 << FNAME_ENTRY_IDBITS) - 1

PROBE_HASH_SHIFT = FNAME_ENTRY_IDBITS
PROBE_HASH_MASK = ~FNAME_ENTRY_IDMASK

SHARD_MASK = FNAME_POOL_SHARDS - 1

assert (SHARD_MASK & PROBE_HASH_MASK) == 0


@dataclass
class FName:
    NO_NUMBER : ClassVar[int] = 0
    IS_NUMBERED_BIT : ClassVar[int] = 0x80000000
    name_idx: int
    number: int

@dataclass
class TopLevelAssetPath:
    package: FName
    asset: FName

@dataclass
class ExportPath:
    class_path: TopLevelAssetPath
    #class_name: FName
    package_name: FName
    object_name: FName

@dataclass
class SoftObjectPath:
    asset_path: TopLevelAssetPath
    sub_path: SerializedString


FGuid: TypeAlias = tuple[int, int, int, int]


@dataclass
class TagMapHandle:
    has_numberless_keys: bool
    handle_num: int
    pair_begin: int


@dataclass
class FValueID:
    TYPE_BITS: ClassVar[int] = 3
    INDEX_BITS: ClassVar[int] = 32-TYPE_BITS
    value_type: ValueTypes
    value_index: int


@dataclass
class AssetIdentifier:
    flags: bytes
    packageName: FName | None
    typeName: FName | None
    objectName: FName | None
    valueName: FName | None

class FNameHeader:
    WIDE_FLAG_BIT = 0b1000000
    def __init__(self, byte_data: bytes):
        self.is_wide = bool(byte_data[0] & self.WIDE_FLAG_BIT)
        self.bytes = byte_data

    @classmethod
    def from_char_len(cls, length: int, is_wide: bool):
        if length >= 1024:
            raise ValueError(f"Max length is 1024, got {length}")

        return cls(bytes((
            (is_wide << 7 | length >> 8),
            length & BITMASK_8
        )))

    def char_len(self):
        return ((self.bytes[0] & ~self.WIDE_FLAG_BIT) << 8) + self.bytes[1]

    def byte_len(self):
        return self.char_len() * (2 if self.is_wide else 1)

    def to_bytes(self):
        return self.bytes