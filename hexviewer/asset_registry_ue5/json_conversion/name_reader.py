import re

from hexviewer.asset_registry_ue5.name_mapper import NameMapper
from hexviewer.asset_registry_ue5.unreal_types import FName, TopLevelAssetPath, ExportPath, SoftObjectPath, \
    AssetIdentifier, SerializedString

EXPORT_PATH_PATTERN = re.compile(r"^(.+\..+)'(.+)\.(.+)'$", re.DOTALL)
SOFT_OBJECT_PATH_PATTERN = re.compile(r"^(.+)::(.+)", re.DOTALL)

class NameReader:

    def __init__(self, name_mapper: NameMapper):
        self.name_mapper = name_mapper

    def read_fname(self, name: str) -> FName:
        return self.name_mapper.fname_from_string(name)

    def read_top_level_path(self, path: str) -> TopLevelAssetPath:
        package, asset = path.split(".", maxsplit=1)
        return TopLevelAssetPath(
            package = self.read_fname(package),
            asset = self.read_fname(asset),
        )

    def read_export_path(self, path: str) -> ExportPath | None:
        if match := EXPORT_PATH_PATTERN.fullmatch(path):
            return ExportPath(
                class_path=self.read_top_level_path(match.group(1)),
                package_name=self.read_fname(match.group(2)),
                object_name=self.read_fname(match.group(3))
            )
        return None

    def read_soft_object_path(self, path: str) -> SoftObjectPath | None:
        if match := SOFT_OBJECT_PATH_PATTERN.fullmatch(path):
            return SoftObjectPath(
                asset_path=self.read_top_level_path(match.group(1)),
                sub_path=SerializedString.from_string(match.group(2))
            )
        return None

    def read_asset_identifier(self, identifier: dict) -> AssetIdentifier:
        return AssetIdentifier(
            flags=identifier.get("Flags"),
            typeName=self.read_fname(identifier.get("Type")),
            packageName=self.read_fname(identifier.get("Package")),
            objectName=self.read_fname(identifier.get("Object")),
            valueName=self.read_fname(identifier.get("Value")),
        )