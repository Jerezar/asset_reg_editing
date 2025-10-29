import logging

from hexviewer.asset_registry_ue5.data_store_reader import DataStore
from hexviewer.asset_registry_ue5.json_conversion.name_resolver import NameResolver
from hexviewer.asset_registry_ue5.name_mapper import NameMapper
from hexviewer.asset_registry_ue5.reader_type import ArchiveType
from hexviewer.asset_registry_ue5.readers.binary_writer import BinaryWriter
from hexviewer.asset_registry_ue5.readers.fname_reader import FNameWriter
from hexviewer.asset_registry_ue5.registry_versions import RegistryVersions
from hexviewer.asset_registry_ue5.types.registry import AssetRegistry, AssetRegistryHeader, AssetRegistryState, \
    AssetData, Bundle, Dependency, PackageData
from hexviewer.asset_registry_ue5.unreal_types import FNameHeader, SoftObjectPath, TopLevelAssetPath, SerializedString

logger = logging.getLogger(__name__)


def write_header_to_binary(header: AssetRegistryHeader, writer: BinaryWriter):
    logger.debug("Writing header")
    writer.write_guid(header.version.guid)
    writer.write_uint32(header.version.version_num)
    writer.write_bool(header.filter_editor_only)


def write_names_as_name_batch(writer: BinaryWriter, names: NameMapper):
    logger.debug("Writing names as name batch")
    num_strings = len(names.names_by_idx)
    writer.write_uint32(num_strings)

    loc_num_string_bytes = writer.tell()
    writer.write_uint32(0)  # placeholder for actual byte amount

    writer.write_uint64(names.HASH_VERSION)

    strings = [
        name.string_view()
        for name in names.names_by_idx
    ]

    hashes = [
        names.make_hash(name.lower())
        for name in strings
    ]

    headers = [
        FNameHeader.from_char_len(len(name), name_serialized.is_wide)
        for name, name_serialized in zip(strings, names.names_by_idx)
    ]

    for name_hash in hashes:
        writer.write_uint64(name_hash)

    for name_header in headers:
        writer.write_bytes(name_header.to_bytes())

    loc_string_bytes_start = writer.tell()

    for serialized_name in names.names_by_idx:
        writer.write_bytes(serialized_name.string_data)

    loc_string_bytes_end = writer.tell()

    writer.seek(loc_num_string_bytes)
    writer.write_uint32(loc_string_bytes_end-loc_string_bytes_start)

    writer.seek(loc_string_bytes_end)


def write_tags_as_data_store(writer: BinaryWriter, tag_store: DataStore, reader_type: ArchiveType):
    logger.debug("Writing tags as data store")
    tag_store.write(writer, reader_type)


def write_bundles(writer: BinaryWriter, bundles: list[Bundle], name_writer: FNameWriter):
    writer.write_int32(len(bundles))

    for bundle in bundles:
        name_writer.write_fname(bundle.bundle_name)
        writer.write_int32(len(bundle.asset_paths))
        for path in bundle.asset_paths:
            name_writer.write_soft_object_path(path)



def write_assets(writer: BinaryWriter, assets: list[AssetData], name_resolver: NameResolver, header: AssetRegistryHeader, reader_type: ArchiveType):
    logger.debug("Writing asset section")
    ver = header.version.version_num
    name_writer = FNameWriter(writer, reader_type)

    def lexical_path(asset: AssetData):

        asset_name = name_resolver.resolve_fname(asset.assetName)

        if asset.optionalOuterPath is not None:
            delim = "."
            outer_str = name_resolver.resolve_fname(asset.optionalOuterPath)

            if outer_str.rfind(delim) >= 0:
                delim = ":"

            return outer_str + delim + asset_name

        else:
            package_name = name_resolver.resolve_fname(asset.packageName)
            return package_name + "." + asset_name



    assets = sorted(assets, key=lambda x: lexical_path(x))

    num_cached = len(assets)
    writer.write_uint32(num_cached)

    for asset in assets:
        if ver < RegistryVersions.REMOVE_ASSET_PATH_FNAMES:
            name_writer.write_fname(asset.oldObjectPath)

        name_writer.write_fname(asset.packagePath)

        if ver >= RegistryVersions.CLASS_PATHS:
            name_writer.write_top_level_asset_path(asset.assetClass)
        else:
            name_writer.write_fname(asset.assetClass)

        name_writer.write_fname(asset.packageName)
        name_writer.write_fname(asset.assetName)

        if ver >= RegistryVersions.REMOVE_ASSET_PATH_FNAMES and not header.filter_editor_only:
            name_writer.write_fname(asset.optionalOuterPath)

        writer.write_tag_map_handle(asset.tags)

        write_bundles(writer, asset.bundles, name_writer)

        write_array(asset.chunk_ids, writer, writer.write_int32)

        writer.write_uint32(asset.package_flags)

    pass


def write_dependencies(writer: BinaryWriter, dependencies: list[Dependency]):
    logger.debug("Writing dependency section")

    loc_dependency_section_bytes = writer.tell()
    writer.write_uint64(0)

    loc_dependency_section_start = writer.tell() # size includes number of dependencies

    writer.write_int32(len(dependencies))

    # TODO parse actual dependencies

    loc_after_dependency_section = writer.tell()

    writer.seek(loc_dependency_section_bytes)
    writer.write_uint64(loc_after_dependency_section - loc_dependency_section_start)

    writer.seek(loc_after_dependency_section)
    pass


def write_package_data(writer: BinaryWriter, packages: list[PackageData]):
    logger.debug("Writing package data")
    writer.write_int32(len(packages))
    # TODO package_data_to_binary
    pass


def write_as_registry_archive(state: AssetRegistryState, writer: BinaryWriter, header: AssetRegistryHeader):
    logger.debug("Writing state as registry archive")
    write_names_as_name_batch(writer, state.names)
    write_tags_as_data_store(writer, state.tag_store, ArchiveType.ASSET_REGISTRY)
    write_assets(writer, state.assets, NameResolver(state.names), header, ArchiveType.ASSET_REGISTRY)
    write_dependencies(writer, state.dependencies)
    write_package_data(writer, state.packages)


def write_state_to_binary(state: AssetRegistryState, writer: BinaryWriter, header: AssetRegistryHeader):
    ver_num = header.version.version_num
    if ver_num < RegistryVersions.FIXED_TAGS:
        #return write_state_as_table_archive(state, writer, header)
        pass
    else:
        return write_as_registry_archive(state, writer, header)


def asset_registry_to_binary_file(registry: AssetRegistry, writer: BinaryWriter):
    logger.info("Writing registry object into binary file")
    write_header_to_binary(registry.header, writer)
    write_state_to_binary(registry.state, writer, registry.header)

    logger.info(f"Wrote file of {writer.tell()} bytes")


def write_array(entries: list, writer: BinaryWriter, element_writer):
    writer.write_int32(len(entries))
    for val in entries:
        element_writer(val)


def write_map(pairs: list[tuple], writer: BinaryWriter, key_writer, element_writer):
    def pair_write(x: tuple):
        key_writer(tuple[0])
        element_writer(tuple[1])

    write_array(pairs, writer,  pair_write)