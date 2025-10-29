import logging
from itertools import batched
from math import ceil
from typing import Literal

from hexviewer.asset_registry_ue5.name_mapper import NameMapper
from hexviewer.asset_registry_ue5.readers.binary_reader import BinaryReader
from hexviewer.asset_registry_ue5.readers.fname_reader import FNameReader
from hexviewer.asset_registry_ue5.data_store_reader import DataStore
from hexviewer.asset_registry_ue5.reader_type import ArchiveType
from hexviewer.asset_registry_ue5.registry_versions import RegistryVersions
from hexviewer.asset_registry_ue5.unreal_types import SerializedString, FNameHeader
from hexviewer.asset_registry_ue5.types.registry import AssetRegVersion, AssetRegistryHeader, AssetData, Dependency, \
    PackageData, Bundle, AssetRegistryState, AssetRegistry

logger = logging.getLogger(__name__)


def asset_registry_from_file(reader: BinaryReader):
    logger.info(f"Latest parsable version: {int(RegistryVersions.LATEST_VERSION)}")
    logger.debug(f"File size: {reader.byte_size} bytes")
    logger.debug(f"File byte order: {reader.file_byte_order}")

    header = read_header(reader)
    state = read_state(reader, header)

    if reader.tell() != reader.byte_size:
        raise ValueError("Reader position not at end of file after parsing")
    else:
        logger.info("File fully parsed")

    return AssetRegistry(
        header, state
    )

def read_header(reader: BinaryReader):
    logger.info("Loading header")

    version_guid = reader.read_guid()
    version_num = reader.read_uint32()
    filter_editor_only = reader.read_bool() if (version_num >= RegistryVersions.ADDED_HEADER) else False

    if version_num > 0x01000000:
        logger.warning(f"Version is {version_num}, possible issue with byteorder?")

    logger.debug(f"Version: {version_num}, FILTER_EDITOR_ONLY set to {filter_editor_only}")

    return AssetRegistryHeader(
        AssetRegVersion(
            version_guid,
            version_num
        ),
        filter_editor_only
    )

def read_state(reader: BinaryReader, header: AssetRegistryHeader):
    logger.info("Loading registry state")

    ver_num = header.version.version_num
    if ver_num < RegistryVersions.REMOVED_MD5_HASH:
        raise ValueError("AssetRegistry version is too old to parse.")

    elif ver_num < RegistryVersions.FIXED_TAGS:
        return read_with_table_archive_reader(reader, header)
    else:
        return read_with_asset_registry_reader(reader, header)



def read_with_table_archive_reader(reader: BinaryReader, header: AssetRegistryHeader):
    logger.info("Using Table Archive Reader")

    names = deserialize_name_table(reader)

    load_asset_data(reader, header, ArchiveType.TABLE_ARCHIVE)


def read_with_asset_registry_reader(reader: BinaryReader, header: AssetRegistryHeader):
    logger.info("Using Asset Registry Reader")

    names = deserialize_name_batch(reader, header)
    tag_store = deserialize_data_store(reader)

    assets = load_asset_data(reader, header, ArchiveType.ASSET_REGISTRY)

    dependencies = get_dependencies(reader, ArchiveType.ASSET_REGISTRY)
    packages = get_package_data(reader, header, ArchiveType.ASSET_REGISTRY)

    return AssetRegistryState(
        names=names,
        tag_store=tag_store,
        assets=assets,
        dependencies=dependencies,
        packages=packages
    )

def deserialize_name_batch(reader: BinaryReader, header: AssetRegistryHeader):
    # CONSTRUCTOR SECTION
    editor_filter = header.filter_editor_only
    # NAMES -> LoadNameBatch -> Construct NameBatchLoader -> read -> load
    #NameBatchLoader.read

    logger.info(f"Loading name batch")
    logger.debug(f"Starting at {hex(reader.tell())}")

    num_strings = reader.read_uint32()

    if num_strings == 0:
        pass
    num_string_bytes = reader.read_uint32()
    hash_version = reader.read_uint64()

    if hash_version != NameMapper.HASH_VERSION:
        logger.error(f"Hash algorithm id is {hash_version}, expected {NameMapper.HASH_VERSION}. Will not be able to convert back.")
    else:
        logger.debug(f"Hash algorithm id: {hash_version}")

    HASH_SIZE = 8
    HEADER_SIZE = 2

    num_hash_bytes = num_strings * HASH_SIZE
    num_header_bytes = num_strings * HEADER_SIZE

    num_bytes_total = num_hash_bytes + num_header_bytes + num_string_bytes

    logger.debug(f"Total name batch size: {num_bytes_total}, "
                 f"{num_strings} strings across {num_string_bytes} bytes, "
                 f"{num_hash_bytes} bytes of hashes, "
                 f"{num_header_bytes} bytes of headers, ")

    byte_order = reader.file_byte_order

    byte_data = reader.read_bytes(num_bytes_total)

    hash_bytes = byte_data[:num_hash_bytes]
    header_bytes = byte_data[num_hash_bytes:num_hash_bytes+num_header_bytes]
    string_bytes = byte_data[-num_string_bytes:]

    logger.debug(f"String_data_start: {hex(reader.tell() - num_string_bytes)}")

    logger.debug(f"Bytes: {len(byte_data)}, hash_bytes: {len(hash_bytes)}, header_bytes: {len(header_bytes)}, string_bytes: {len(string_bytes)}")

    # hashes = [    # discard hashes, recreate later
    #     int.from_bytes(b, byte_order)
    #     for b in batched(hash_bytes, HASH_SIZE)
    # ]

    string_headers = [
        FNameHeader(bytes(b))
        for b in batched(header_bytes, HEADER_SIZE)
    ]

    logger.debug("Checking headers:")
    logger.debug(f"num strings with length above char limit (1023): {len([head for head in string_headers if head.char_len() >= 1024])}")
    logger.debug(f"num_string_bytes: {sum([head.byte_len() for head in string_headers])}")

    #NameBatchLoader.load -> LoadSeparatedNameBatch

    strings = []
    offset = 0

    for header in string_headers:
        strings.append(
            SerializedString(
                string_bytes[offset:offset+header.byte_len()],
                header.is_wide
            )
        )
        offset += header.byte_len()

    if offset != num_string_bytes:
        raise ValueError(f"Tried to parse {offset} string bytes when {num_string_bytes} was specified")


    return NameMapper(
        names=strings,
    )

def deserialize_name_table(reader: BinaryReader):
    # CONSTRUCTOR SECTION
    name_map = []
    table_offset = reader.read_int64()

    if table_offset > reader.byte_size:
        raise ValueError("Name table offset lies outside of file, file may be corrupted.")

    pre_read_offset = reader.tell()
    reader.seek(table_offset)

    num_names = reader.read_int32()
    if num_names < 0:
        raise ValueError("Name table holds less than 0 names, file may be corrupted")

    for i in range(num_names):
        name_map.append(reader.read_serialized_fname())

    reader.seek(pre_read_offset)
    # END CONSTRUCTOR SECTION
    return name_map

def deserialize_data_store(reader: BinaryReader):
    store_reader = DataStore()
    store_reader.load(reader, ArchiveType.ASSET_REGISTRY)
    return store_reader


def load_asset_data(reader:BinaryReader, header: AssetRegistryHeader, reader_mode:Literal[
    ArchiveType.TABLE_ARCHIVE, ArchiveType.ASSET_REGISTRY]):
    logger.info("Loading asset data")
    logger.debug(f"Starting at {hex(reader.tell())}")

    if header.version.version_num == int(RegistryVersions.LATEST_VERSION):
        return load_assets(reader, header, reader_mode)

    else:
        #return load_assets__old(reader, header, reader_mode)
        raise ValueError("Didn't implement this yet, sorry")

def load_assets(reader, header, reader_mode):
    return get_cached_asset(reader, header, reader_mode)


def get_bundles(reader: BinaryReader, header: AssetRegistryHeader, reader_type:ArchiveType):


    if header.version.version_num == RegistryVersions.LATEST_VERSION:
        return load_bundles(reader, header, reader_type)
    else:
        #load_bundles_old(reader, header, reader_type)
        pass #TODO

def load_bundles(reader: BinaryReader, header: AssetRegistryHeader, reader_type: ArchiveType):
    #logger.debug(f"Reading bundles for asset at {hex(reader.tell())}")

    fname_reader = FNameReader(reader, reader_type)

    bundles = []
    num_bundles = reader.read_int32()
    #logger.debug(f"{num_bundles} bundles")

    for i in range(num_bundles):
        bundle_name = fname_reader.read_fname()
        num_asset_paths = reader.read_int32()

        logger.debug(f"{num_asset_paths} paths")

        asset_paths = []

        for j in range(num_asset_paths):
            asset_path = fname_reader.read_soft_object_path()
            asset_paths.append(asset_path)

        bundles.append(Bundle(bundle_name, asset_paths))

    return bundles



def get_cached_asset(reader: BinaryReader, header: AssetRegistryHeader, reader_type:ArchiveType):
    logger.info("Loading assets")

    ver = header.version.version_num
    fname_reader = FNameReader(reader, reader_type)

    num_cached = reader.read_int32()
    logger.debug(f"{num_cached} assets to load")

    cached_assets = []
    for i in range(num_cached):
        old_object_path = fname_reader.read_fname() if ver < RegistryVersions.REMOVE_ASSET_PATH_FNAMES else None
        package_path = fname_reader.read_fname()

        if ver >= RegistryVersions.CLASS_PATHS:
            asset_class = fname_reader.read_top_level_asset_path()
        else:
            asset_class = fname_reader.read_fname()

        package_name = fname_reader.read_fname()
        asset_name = fname_reader.read_fname()

        optional_outer_path = None
        if ver >= RegistryVersions.REMOVE_ASSET_PATH_FNAMES and not header.filter_editor_only:
            optional_outer_path = fname_reader.read_fname()

        #load tags and bundles
        tags = reader.read_tag_map_handle()

        bundles = get_bundles(reader, header, reader_type)

        chunk_ids = read_array(reader, reader.read_int32)

        package_flags = reader.read_uint32()

        cached_assets.append(AssetData(
            packagePath=package_path,
            oldObjectPath=old_object_path,
            assetClass=asset_class,
            packageName=package_name,
            assetName=asset_name,
            optionalOuterPath=optional_outer_path,
            tags=tags,
            bundles=bundles,
            chunk_ids=chunk_ids,
            package_flags=package_flags,
        ))

    logger.debug("Does total width of referenced handles match tag store?")
    logger.debug(f"Sum of numberless handles: {sum([asset.tags.handle_num for asset in cached_assets if asset.tags.has_numberless_keys])}")
    logger.debug(f"Sum of numbered handles: {sum([asset.tags.handle_num for asset in cached_assets if not asset.tags.has_numberless_keys])}")

    return cached_assets





PACKAGE_DEP_FLAG_BITS = 5
NAME_DEP_FLAG_BITS = 0
MANAGE_DEP_FLAG_BITS = 1
REFERENCER_FLAG_BITS = 0

def get_dependencies(reader: BinaryReader, reader_type: ArchiveType):
    logger.info("Loading dependencies")
    dependency_section_size = reader.read_int64()
    num_dependencies = reader.read_int32()

    fname_reader = FNameReader(reader, reader_type)

    dependencies = []

    for i in range(num_dependencies):
        identifier = fname_reader.read_asset_identifier()

        package_deps, package_dep_flags = get_dependency_list(reader, PACKAGE_DEP_FLAG_BITS)
        name_deps, name_dep_flags = get_dependency_list(reader, NAME_DEP_FLAG_BITS)
        manage_deps, manage_dep_flags = get_dependency_list(reader, MANAGE_DEP_FLAG_BITS)
        referencers, referencer_flags = get_dependency_list(reader, REFERENCER_FLAG_BITS)

        dependencies.append(Dependency(
            identifier,
            package_deps,
            package_dep_flags,
            name_deps,
            name_dep_flags,
            manage_deps,
            manage_dep_flags,
            referencers,
            referencer_flags,
        ))

    return dependencies

def get_dependency_list(reader: BinaryReader, bits_per_flag):
    deps = read_array(reader, reader.read_int32)
    flags = reader.read_bytes(get_bytes_for_packed_flags(len(deps), bits_per_flag))

    return deps, flags


BITS_PER_WORD = 32
def get_bytes_for_packed_flags(bits_per_flag, n_flags):
    return ceil((bits_per_flag*n_flags)/BITS_PER_WORD)

def get_package_data(reader: BinaryReader, header:AssetRegistryHeader, reader_mode: ArchiveType):
    logger.info("Loading Packages")
    ver_num = header.version.version_num
    fname_reader = FNameReader(reader, reader_mode)

    packages = []

    num_package_data = reader.read_int32()

    for i in range(num_package_data):
        ue4_ver = None
        ue5_ver = None
        version_licensee = None
        flags = None
        cooked_hash = None
        chunk_hashes=None
        custom_versions=None
        imported_classes=None
        extension_path=None

        key = fname_reader.read_fname()
        # serialized FAssetPackageData
        package_disk_size = reader.read_int64()
        guid = reader.read_guid()

        if ver_num >= RegistryVersions.ADDED_COOKED_MD5_HASH:
            cooked_hash = reader.read_bytes(16)

        if ver_num >= RegistryVersions.ADDED_CHUNK_HASHES:
            chunk_hashes = read_map(reader, 12, 20)


        if ver_num >= RegistryVersions.WORKSPACE_DOMAIN:
            ue4_ver = reader.read_int32()
            if ver_num >= RegistryVersions.PACKAGE_FILE_SUMMARY_VERSION_CHANGE:
                ue5_ver = reader.read_int32()
            version_licensee = reader.read_int32()
            flags = reader.read_int32()

            num_custom_versions = reader.read_int32()
            custom_versions = [
               (reader.read_guid(), reader.read_int32())
                for _ in range(num_custom_versions)
            ]

        if ver_num >= RegistryVersions.PACKAGE_IMPORTED_CLASSES:
            imported_classes = read_array(reader, fname_reader.read_fname)

        if ver_num >= RegistryVersions.ASSET_PACKAGE_DATA_HAS_EXTENSION:
            extension_path = reader.read_fstring()

        packages.append(PackageData(
            key,
            package_disk_size,
            guid,
            cooked_hash,
            chunk_hashes,
            ue4_ver,
            ue5_ver,
            version_licensee,
            flags,
            custom_versions,
            imported_classes,
            extension_path
        ))

    return packages


def read_array(reader: BinaryReader, element_getter):
    num_entries = reader.read_int32()
    entries = [
        element_getter()
        for _ in range(num_entries)
    ]
    return entries


def read_map(reader: BinaryReader, key_size, element_size):
    num_entries = reader.read_int32()

    return [
        (reader.read_bytes(key_size), reader.read_bytes(element_size))
        for _ in range(num_entries)
    ]

