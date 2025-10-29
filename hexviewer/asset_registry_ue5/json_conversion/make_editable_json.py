import logging
from binascii import hexlify, unhexlify
from typing import Callable

from hexviewer.asset_registry_ue5.data_store_reader import DataStore
from hexviewer.asset_registry_ue5.json_conversion.name_resolver import NameResolver
from hexviewer.asset_registry_ue5.json_conversion.tag_value_type_markers import MARKERS_BY_TYPE
from hexviewer.asset_registry_ue5.registry_versions import RegistryVersions
from hexviewer.asset_registry_ue5.tag_value_types import ValueTypes
from hexviewer.asset_registry_ue5.types.registry import AssetData, AssetRegistryState, AssetRegistry, \
    AssetRegistryHeader, Dependency, PackageData
from hexviewer.asset_registry_ue5.unreal_types import SerializedString

logger = logging.getLogger(__name__)


def header_to_json(header):
    logger.info("Serializing header")
    return {
        "VersionGUID": header.version.guid,
        "VersionNumber": header.version.version_num,
        "FilterEditorOnly": header.filter_editor_only,
    }

def assets_to_json(assets: list[AssetData], header: AssetRegistryHeader, tag_store: DataStore, name_resolver: NameResolver):
    logger.debug("Serializing assets")
    asset_out: list[dict] = []

    ver = header.version.version_num

    #_debug_val_type_count: Counter = Counter()

    identity = lambda x: x

    value_resolvers: dict[ValueTypes, Callable[[any], str]] = {
        ValueTypes.AnsiString: identity,
        ValueTypes.WideString: identity,
        ValueTypes.NumberlessName: name_resolver.resolve_fname,
        ValueTypes.Name: name_resolver.resolve_fname,
        ValueTypes.NumberlessExportPath: name_resolver.resolve_export_path,
        ValueTypes.ExportPath: name_resolver.resolve_export_path,
        ValueTypes.LocalizedText: SerializedString.string_view,
    }

    for asset in assets:
        asset_name = name_resolver.resolve_fname(asset.assetName)

        if ver >= RegistryVersions.CLASS_PATHS:
            asset_class = name_resolver.resolve_top_level_path(asset.assetClass)
        else:
            asset_class = name_resolver.resolve_fname(asset.assetClass)

        package_path = name_resolver.resolve_fname(asset.packagePath)
        package_name = name_resolver.resolve_fname(asset.packageName)

        old_object_path = name_resolver.resolve_fname(asset.oldObjectPath)
        optional_outer_path = name_resolver.resolve_fname(asset.optionalOuterPath)

        tags = tag_store.get_key_val_pair(asset.tags)

        tags_out = {}
        for tag_name_handle, val_id in tags:
            tag_name = name_resolver.resolve_fname(tag_name_handle)
            tag_type = MARKERS_BY_TYPE[val_id.value_type]

            tag_value = tag_store.get_value(val_id)
            tag_value_out = value_resolvers.get(val_id.value_type)(tag_value)

            tags_out[tag_name] = f"{tag_type}({tag_value_out})"

        bundles_out = []
        for bundle in asset.bundles:
            bundles_out.append({
                "BundleName": name_resolver.resolve_fname(bundle.bundle_name),
                "AssetPaths": [
                    name_resolver.resolve_soft_object_path(path)
                    for path in bundle.asset_paths
                ],
            })


        asset_out.append({
            "PackageName": package_name,
            "PackagePath": package_path,
            "AssetName": asset_name,
            "AssetClass": asset_class,
            "HasNumberlessTags": asset.tags.has_numberless_keys,
            "TagsAndValues": tags_out,
            "Bundles": bundles_out,
            "PackageFlags": asset.package_flags,
            "ChunkIds": asset.chunk_ids,
            "OldObjectPath": old_object_path,
            "OptionalOuterPath": optional_outer_path,
        })

    return asset_out


def dependencies_to_json(dependencies: list[Dependency], name_resolver: NameResolver):
    logger.debug("Serializing dependencies")
    dependencies_out = []
    for dependency in dependencies:
        dep_out = {
            "AssetIdentifier": name_resolver.resolve_asset_identifier(dependency.identifier),
            "PackageDependencies": [hex(node_idx) for node_idx in dependency.package_deps],
            "PackageDepFlags": dependency.package_dep_flags,
            "NameDependencies": [hex(node_idx) for node_idx in dependency.name_deps],
            "NameDepFlags": dependency.name_dep_flags,
            "ManageDependencies": [hex(node_idx) for node_idx in dependency.manage_deps],
            "ManageDepFlags": dependency.manage_dep_flags,
            "Referencers": [hex(node_idx) for node_idx in dependency.referencers],
            "ReferencerFlags": dependency.referencer_flags,
        }
        dependencies_out.append(dep_out)

    return dependencies_out


def packages_to_json(packages: list[PackageData], name_resolver:NameResolver):
    logger.debug("Serializing package data")
    packages_out = []
    for package in packages:
        packages_out.append({
            "Key": name_resolver.resolve_fname(package.key),
            "ByteSize": package.size_on_disk,
            "GUID": package.guid,
            "CookedHash": package.cooked_hash,
            "ChunkHashes": [
                {"ChunkID": chunk_id, "ChunkHash": chunk_hash}
                for chunk_id, chunk_hash in package.chunk_hashes
            ],
            "UE4Version": package.ue4_ver,
            "UE5Version": package.ue5_ver,
            "VersionLicensee": package.version_licensee,
            "Flags": package.flags,
            "CustomVersions": [
                {"VersionKey": guid, "VersionNumber": number}
                for guid, number in package.custom_versions
            ],
            "ImportedClasses": [
                name_resolver.resolve_fname(name)
                for name in package.imported_classes
            ],
            "ExtensionPath": package.extension_path.string_view()
        })

    return packages_out



def state_to_json(state: AssetRegistryState, header: AssetRegistryHeader):
    logger.debug("Serializing state")

    options = {
        "TextTagsFirst": state.tag_store.text_first
    }

    name_resolver = NameResolver(state.names)
    logger.debug(f"{len(state.names.names_by_idx)} known FNames")

    assets_serialized = assets_to_json(state.assets, header, state.tag_store, name_resolver)
    dependencies_serialized = dependencies_to_json(state.dependencies, name_resolver)
    packages_serialized = packages_to_json(state.packages, name_resolver)

    return {
        "Assets": assets_serialized,
        "Dependencies": dependencies_serialized,
        "Packages":packages_serialized,
        "Options": options
    }


def make_editable_json(registry: AssetRegistry):
    logger.info("Writing registry object into json file")
    header_serialized = header_to_json(registry.header)

    state_serialized = state_to_json(registry.state, registry.header)

    return {
        "Header": header_serialized,
        "State": state_serialized,
    }
