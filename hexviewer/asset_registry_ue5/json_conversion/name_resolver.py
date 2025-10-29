from hexviewer.asset_registry_ue5.name_mapper import NameMapper
from hexviewer.asset_registry_ue5.unreal_types import FName, TopLevelAssetPath, ExportPath, SerializedString, \
    SoftObjectPath, AssetIdentifier


class NameResolver:

    def __init__(self, name_mapper: NameMapper):
        self.name_mapper = name_mapper

    def resolve_fname(self, name: FName) -> str:
        return self.name_mapper.string_from_fname(name)

    def resolve_top_level_path(self, path: TopLevelAssetPath):
        return self.resolve_fname(path.package) + "." + self.resolve_fname(path.asset)

    def resolve_export_path(self, path: ExportPath):
        return f"{self.resolve_top_level_path(path.class_path)}'{self.resolve_fname(path.package_name)}.{self.resolve_fname(path.object_name)}'"

    def resolve_soft_object_path(self, path: SoftObjectPath):
        return f"{self.resolve_top_level_path(path.asset_path)}::{path.sub_path.string_view()}"

    def resolve_asset_identifier(self, identifier:AssetIdentifier):
        return {
            "Flags": identifier.flags,
            "Type": self.resolve_fname(identifier.typeName),
            "Package": self.resolve_fname(identifier.packageName),
            "Object": self.resolve_fname(identifier.objectName),
            "Value": self.resolve_fname(identifier.valueName),
        }