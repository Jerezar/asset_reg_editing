import logging
import re
from collections.abc import Callable

from hexviewer.asset_registry_ue5.data_store_reader import DataStore
from hexviewer.asset_registry_ue5.json_conversion.name_reader import NameReader
from hexviewer.asset_registry_ue5.json_conversion.tag_value_type_markers import TYPES_BY_MARKER
from hexviewer.asset_registry_ue5.name_mapper import NameMapper
from hexviewer.asset_registry_ue5.registry_versions import RegistryVersions
from hexviewer.asset_registry_ue5.tag_value_types import ValueTypes
from hexviewer.asset_registry_ue5.types.registry import AssetRegistry, AssetRegistryHeader, AssetRegVersion, \
    AssetRegistryState, AssetData, Bundle
from hexviewer.asset_registry_ue5.unreal_types import SerializedString

logger = logging.getLogger(__name__)

TYPED_TAG_VAL_PATTERN = re.compile(r"^([A-Z_]+)\((.*)\)$", re.DOTALL)

def parse_typed_tag_value(val: str) -> tuple[ValueTypes, str] | None:
    if match := re.fullmatch(TYPED_TAG_VAL_PATTERN, val):
        return TYPES_BY_MARKER.get(match.group(1)), match.group(2)
    else:
        print(val),



def parse_header(header_dict) -> AssetRegistryHeader:
    logger.info("Loading header")
    return AssetRegistryHeader(
        version=AssetRegVersion(
            guid=header_dict["VersionGUID"],
            version_num=header_dict["VersionNumber"],
        ),
        filter_editor_only=bool(header_dict["FilterEditorOnly"])
    )

def parse_assets(assets: list[dict], name_mapper: NameReader, header: AssetRegistryHeader, options: dict) -> tuple[list[AssetData], DataStore | None]:
    logger.info("Loading assets")
    ver = header.version.version_num

    assets_out = []

    data_store = DataStore()
    data_store.text_first = options.get("TextTagsFirst", False)

    identity = lambda x: x

    value_resolvers: dict[ValueTypes, Callable[[str], any]] = {
        ValueTypes.AnsiString: identity,
        ValueTypes.WideString: identity,
        ValueTypes.NumberlessName: name_mapper.read_fname,
        ValueTypes.Name: name_mapper.read_fname,
        ValueTypes.NumberlessExportPath: name_mapper.read_export_path,
        ValueTypes.ExportPath: name_mapper.read_export_path,
        ValueTypes.LocalizedText: SerializedString.from_string,
    }

    for asset in assets:
        package_name = name_mapper.read_fname(asset.get("PackageName"))
        package_path = name_mapper.read_fname(asset.get("PackagePath"))

        asset_name = name_mapper.read_fname(asset.get("AssetName"))

        if ver >= RegistryVersions.CLASS_PATHS:
            asset_class = name_mapper.read_top_level_path(asset.get("AssetClass"))
        else:
            asset_class = name_mapper.read_fname(asset.get("AssetClass"))

        has_numberless_keys = asset.get("HasNumberlessTags")

        tag_val_pairs = []

        for name, tag in asset.get("TagsAndValues", {}).items():
            tag_name = name_mapper.read_fname(name)
            tag_type, tag_value = parse_typed_tag_value(tag)

            val = value_resolvers[tag_type](tag_value)

            val_ref = data_store.insert_value(val, tag_type)
            tag_val_pairs.append((tag_name, val_ref))

        tags = data_store.register_map_pairs(tag_val_pairs, has_numberless_keys)
            
        bundles_out = []
        for bundle in asset.get("Bundles", []):
            bundle_name = name_mapper.read_fname(bundle.get("BundleName"))
            asset_paths = [
                name_mapper.read_soft_object_path(path)
                for path in bundle.get("AssetPaths", [])
            ]
            bundles_out.append(Bundle(
                bundle_name=bundle_name,
                asset_paths=asset_paths,
            ))

        package_flags = asset.get("PackageFlags")
        chunk_ids = asset.get("ChunkIds")

        old_object_path = name_mapper.read_fname(asset.get("OldObjectPath"))
        optional_outer_path = name_mapper.read_fname(asset.get("OptionalOuterPath"))

        assets_out.append(
            AssetData(
                packagePath=package_path,
                packageName=package_name,
                assetName=asset_name,
                assetClass=asset_class,
                tags=tags,
                bundles=bundles_out,
                chunk_ids=chunk_ids,
                package_flags=package_flags,
                oldObjectPath=old_object_path,
                optionalOuterPath=optional_outer_path
            )
        )

    logger.info(f"{len(assets_out)} assets loaded")

    return assets_out, data_store


def parse_state(state_reg: dict, header: AssetRegistryHeader) -> AssetRegistryState:
    logger.info("Loading state")
    options = state_reg.get("Options", {})

    names = NameMapper()
    fname_reader = NameReader(names)
    assets, tag_store = parse_assets(state_reg.get("Assets",  []), fname_reader, header, options)
    dependencies = [] #TODO
    packages = [] #TODO

    logger.debug(f"Registered {len(names.names_by_idx)} FNames")

    return AssetRegistryState(
        names=names,
        assets=assets,
        tag_store=tag_store,
        dependencies=dependencies,
        packages=packages,
    )


def load_registry_from_json(json_reg: dict) -> AssetRegistry:
    logger.info("Parsing asset registry from json")
    header = parse_header(json_reg.get("Header"))
    state = parse_state(json_reg.get("State"), header)
    return AssetRegistry(
        header=header,
        state=state
    )