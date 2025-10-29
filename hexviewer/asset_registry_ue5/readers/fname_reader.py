from typing import Callable

from hexviewer.asset_registry_ue5.readers.binary_reader import BinaryReader
from hexviewer.asset_registry_ue5.readers.binary_writer import BinaryWriter
from hexviewer.asset_registry_ue5.reader_type import ArchiveType
from hexviewer.asset_registry_ue5.unreal_types import FName, ExportPath, SoftObjectPath, TopLevelAssetPath, FValueID, \
    AssetIdentifier


class FNameReader:
    """Reads things that depend on FNames and therefor depend on ReaderType"""
    def __init__(self, reader: BinaryReader, reader_type: ArchiveType):
        self.reader = reader
        self.read_fname = self.read_fname__table_archive if reader_type == ArchiveType.TABLE_ARCHIVE else self.read_fname__asset_registry

    def read_fname__table_archive(self):
        return FName(0, 0)  # TODO

    def read_fname__asset_registry(self):
        index = self.reader.read_uint32()
        number = FName.NO_NUMBER

        if index & FName.IS_NUMBERED_BIT:
            index -= FName.IS_NUMBERED_BIT
            number = self.reader.read_uint32()

        return FName(
            index,
            number
        )

    def read_export_path(self):
        class_path = self.read_top_level_asset_path()
        #class_name = self.read_fname()
        object_name = self.read_fname()
        package_name = self.read_fname()

        return ExportPath(
            class_path=class_path,
            #class_name=class_name,
            package_name=package_name,
            object_name=object_name
        )

    def read_key_val_pair(self):
        return self.read_fname(), self.reader.read_value_id()

    def read_soft_object_path(self):
        res = SoftObjectPath(
            self.read_top_level_asset_path(),
            self.reader.read_fstring()
        )
        return res

    def read_top_level_asset_path(self):
        class_path_package_name = self.read_fname()
        class_path_asset_name = self.read_fname()

        return TopLevelAssetPath(
            class_path_package_name,
            class_path_asset_name
        )

    def read_asset_identifier(self):
        flags = self.reader.read_uint8()
        packageName = None
        typeName = None
        objectName = None
        valueName = None


        if flags & (1 << 0):
            packageName = self.read_fname()

        if flags & (1 << 1):
            typeName = self.read_fname()

        if flags & (1 << 2):
            objectName = self.read_fname()

        if flags & (1 << 3):
            valueName = self.read_fname()

        return AssetIdentifier(flags, packageName, typeName, objectName, valueName)


class FNameWriter:
    """Reads things that depend on FNames and therefor depend on ReaderType"""
    def __init__(self, writer: BinaryWriter, reader_type: ArchiveType):
        self.writer = writer
        self.write_fname: Callable[[FName],None] = self.write_fname__table_archive if reader_type == ArchiveType.TABLE_ARCHIVE else self.write_fname__asset_registry

    def write_fname__table_archive(self, val: FName):
        pass  # TODO

    def write_fname__asset_registry(self, val: FName):
        if val.number == FName.NO_NUMBER:
            self.writer.write_uint32(val.name_idx)
        else:
            self.writer.write_uint32(val.name_idx | FName.IS_NUMBERED_BIT)
            self.writer.write_uint32(val.number)

    def write_export_path(self, path: ExportPath):
        self.write_top_level_asset_path(path.class_path)

        #self.write_fname(path.class_name)
        self.write_fname(path.object_name)
        self.write_fname(path.package_name)

    def write_key_val_pair(self, pair: tuple[FName, FValueID]):
        name, val = pair
        self.write_fname(name)
        self.writer.write_value_id(val)

    def write_soft_object_path(self, path: SoftObjectPath):
        self.write_top_level_asset_path(path.asset_path)
        self.writer.write_fstring(path.sub_path)

    def write_top_level_asset_path(self, path: TopLevelAssetPath):
        self.write_fname(path.package)
        self.write_fname(path.asset)
