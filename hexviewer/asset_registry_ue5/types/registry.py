from dataclasses import dataclass

from hexviewer.asset_registry_ue5.data_store_reader import DataStore
from hexviewer.asset_registry_ue5.name_mapper import NameMapper
from hexviewer.asset_registry_ue5.unreal_types import FName, SoftObjectPath, FGuid, \
    SerializedString, TagMapHandle, TopLevelAssetPath, AssetIdentifier


@dataclass
class AssetRegVersion:
    guid: FGuid
    version_num: int

    # @classmethod
    # def from_bytes(cls, reader) -> Self:
    #     guid = reader.read(16)
    #     version_num = int.from_bytes(reader.read(4), signed=True)
    #     return cls(guid, version_num)


@dataclass
class AssetRegistryHeader:
    version: AssetRegVersion
    filter_editor_only: bool

    # @classmethod
    # def from_bytes(cls, reader) -> Self:
    #     version = AssetRegVersion.from_bytes(reader)
    #     filter_editor_only = reader.read(1) # TODO check actual cpp bool size
    #     return cls(version, filter_editor_only)


@dataclass
class Bundle:
    bundle_name: FName
    asset_paths: list[SoftObjectPath]

@dataclass
class AssetData:
    packagePath: FName
    packageName: FName
    assetClass: FName | TopLevelAssetPath
    assetName: FName
    tags: TagMapHandle
    bundles: list[Bundle]
    chunk_ids: list[int]
    package_flags: int
    oldObjectPath: FName | None
    optionalOuterPath: FName | None


@dataclass
class Dependency:
    identifier: AssetIdentifier

    package_deps: list[int]
    package_dep_flags: bytes

    name_deps: list[int]
    name_dep_flags: bytes

    manage_deps: list[int]
    manage_dep_flags: bytes

    referencers: list[int]
    referencer_flags: bytes


@dataclass
class PackageData:
    key: FName
    size_on_disk: int
    guid: FGuid
    cooked_hash: bytes
    chunk_hashes: list[tuple[bytes, bytes]]
    ue4_ver: int
    ue5_ver: int
    version_licensee: int
    flags: int
    custom_versions: list[tuple[FGuid, int]]
    imported_classes: list[FName]
    extension_path: SerializedString


@dataclass
class AssetRegistryState:
    names: NameMapper
    assets: list[AssetData]
    dependencies: list[Dependency]
    packages: list[PackageData]
    tag_store: DataStore


@dataclass
class AssetRegistry:
    header: AssetRegistryHeader
    state: AssetRegistryState
