from enum import IntEnum


class ArchiveType(IntEnum):
    """Represents the ArchiveReader used internally in Unreal, mostly relevant for the way FNames are stored"""
    TABLE_ARCHIVE = 1
    ASSET_REGISTRY = 2
