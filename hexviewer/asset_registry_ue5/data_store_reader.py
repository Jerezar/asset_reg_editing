import logging

from cityhash import CityHash64

from hexviewer.asset_registry_ue5.readers.binary_writer import BinaryWriter
from hexviewer.asset_registry_ue5.reader_type import ArchiveType
from hexviewer.asset_registry_ue5.readers.binary_reader import BinaryReader
from hexviewer.asset_registry_ue5.readers.fname_reader import FNameReader, FNameWriter
from hexviewer.asset_registry_ue5.tag_value_types import ValueTypes
from hexviewer.asset_registry_ue5.unreal_types import FName, TagMapHandle, FValueID, SerializedString, ExportPath
from hexviewer.asset_registry_ue5.utils import encode_no_bom

logger = logging.getLogger(__name__)

DATASTORE_START_NEW = 0x12345679
DATASTORE_START_OLD = 0x12345678
DATASTORE_END = 0x87654321

class DataStore:

    def __init__(self):
        self.numbered_pairs = []
        self.numberless_pairs = []

        self.texts: list[SerializedString] = []
        self.ansi_strings: list[str] = []
        self.wide_strings: list[str] = []
        self.numberless_export_paths: list[ExportPath] = []
        self.export_paths: list[ExportPath]  = []
        self.names: list[FName] = []
        self.numberless_names: list[FName] = []

        self.text_first = False

        self.hash_tables_by_type: dict[ValueTypes, dict[int, int]] = {
            ValueTypes.LocalizedText: {},
            ValueTypes.AnsiString: {},
            ValueTypes.WideString: {},
            ValueTypes.Name: {},
            ValueTypes.NumberlessName: {},
            ValueTypes.ExportPath: {},
            ValueTypes.NumberlessExportPath: {},
        }

    def get_key_val_pair(self, handle: TagMapHandle) -> list[tuple[FName, FValueID]]:
        if handle.has_numberless_keys:
            table = self.numberless_pairs
        else:
            table = self.numbered_pairs

        return table[ handle.pair_begin : handle.pair_begin + handle.handle_num]

    def get_value(self, val_idx: FValueID):
        table = self.get_table_by_type(val_idx.value_type)

        if table is None:
            logger.error("Unable to access corresponding table")
            return None

        try:
            return table[val_idx.value_index]
        except IndexError:
            raise IndexError(f"Index {val_idx.value_index} out of range for type {val_idx.value_type}")

    def load(self, reader: BinaryReader, reader_mode: ArchiveType):
        logger.info("Loading tag store")
        logger.debug(f"Starting at {hex(reader.tell())}")

        # number names          DisplayEntryID              FName
        # names                 FName                       FName
        # numbered exports      NumberlessExportPath        AssetRegistryExportPath
        # exports               AssetRegistryExportPath     AssetRegistryExportPath
        # texts                 MarshalledText              FString
        # ansioffsets           uint32                      uint32
        # wide offsets          uin32                       uint32
        # ansistrings           String                      String
        # wide strings          WideString                  WideString
        # numberless pairs      NumberlessPair              FName + uint32
        # pairs                 NumberedPair                FName + uint32

        start_marker = reader.read_uint32()
        if start_marker not in [DATASTORE_START_NEW, DATASTORE_START_OLD]:
            raise ValueError("Invalid start marker for tag data store")
        else:
            logger.debug("Valid start marker")

        array_sizes = {
            "NumberlessNames": reader.read_uint32(),
            "Names": reader.read_uint32(),
            "NumberlessExportPaths": reader.read_uint32(),
            "ExportPaths": reader.read_uint32(),
            "Texts": reader.read_uint32(),
            "AnsiStringOffsets": reader.read_uint32(),
            "WideStringOffsets": reader.read_uint32(),
            "AnsiStrings": reader.read_uint32(),
            "WideStrings": reader.read_uint32(),
            "NumberlessPairs": reader.read_uint32(),
            "Pairs": reader.read_uint32(),
        }

        logger.debug(array_sizes)

        self.text_first: bool = start_marker == DATASTORE_START_NEW

        fname_reader = FNameReader(reader, reader_mode)

        self.texts = None

        if self.text_first:
            num_text_bytes = reader.read_uint32()
            logger.debug(f"Reading TEXT tags at {hex(reader.tell())}")
            loc_pre_read = reader.tell()

            self.texts = self.load_table(array_sizes.get("Texts", 0), reader.read_fstring)

            num_bytes_read = reader.tell() - loc_pre_read

            if num_text_bytes != num_bytes_read:
                raise ValueError(f"Parsed {num_bytes_read} bytes of text when {num_text_bytes} were specified")
            else:
                logger.debug(f"Read {num_text_bytes} bytes of text tags")

        logger.debug(f"Reading numberless names at {hex(reader.tell())}")
        self.numberless_names = self.load_table(array_sizes.get("NumberlessNames", 0), fname_reader.read_fname)
        logger.debug(f"Reading numbered names at {hex(reader.tell())}")
        self.names = self.load_table(array_sizes.get("Names", 0), fname_reader.read_fname)
        logger.debug(f"Reading numberless paths at {hex(reader.tell())}")
        self.numberless_export_paths = self.load_table(array_sizes.get("NumberlessExportPaths", 0), fname_reader.read_export_path)
        logger.debug(f"Reading numbered paths at {hex(reader.tell())}")
        self.export_paths = self.load_table(array_sizes.get("ExportPaths", 0), fname_reader.read_export_path)

        if not self.text_first:
            logger.debug(f"Reading TEXT tags at {hex(reader.tell())}")
            self.texts = self.load_table(array_sizes.get("Texts", 0), reader.read_fstring)


        # ------READ BUT DISCARD------ #
        logger.debug(f"Reading ANSI offsets at {hex(reader.tell())}")
        string_offsets = self.load_table(array_sizes.get("AnsiStringOffsets", 0), reader.read_uint32)
        logger.debug(f"Reading WIDE offsets at {hex(reader.tell())}")
        wide_string_offsets = self.load_table(array_sizes.get("WideStringOffsets", 0), reader.read_uint32)
        # ------READ BUT DISCARD------ #

        logger.debug(f"Reading ANSI texts at {hex(reader.tell())}")
        self.ansi_strings = reader.read_bytes(1 * array_sizes.get("AnsiStrings", 0)).decode(encoding="utf-8").split("\x00")[:-1] # last nullterminator causes an empty string split
        logger.debug(f"Reading WIDE texts at {hex(reader.tell())}")
        self.wide_strings = reader.read_bytes(2 * array_sizes.get("WideStrings", 0)).decode(encoding="utf-16").split("\x00")[:-1]

        logger.debug(len(self.ansi_strings))
        logger.debug(len(self.wide_strings))

        self.numberless_pairs = self.load_table(array_sizes.get("NumberlessPairs", 0), fname_reader.read_key_val_pair)
        self.numbered_pairs = self.load_table(array_sizes.get("Pairs", 0), fname_reader.read_key_val_pair)

        logger.debug(f"End data store read at {hex(reader.tell())}")

        end_marker = reader.read_uint32()
        if end_marker != DATASTORE_END:
            raise ValueError("End marker for tag datastore is invalid, possibly corrupted")
        else:
            logger.debug("Valid end marker")

        #self.set_up_hashes()

        logger.debug({
            val_type: len(self.get_table_by_type(val_type))
            for val_type in ValueTypes
        })

        logger.debug("Finished setting up tag store")


    def write(self, writer: BinaryWriter, archive_type: ArchiveType, text_first: bool | None = None):
        logger.info("Writing tag store")
        logger.debug(f"Starting at {hex(writer.tell())}")
        if text_first is None:
            text_first = self.text_first

        fname_writer = FNameWriter(writer, archive_type)

        writer.write_uint32(DATASTORE_START_NEW if text_first else DATASTORE_START_OLD)

        ansi_offsets = []
        wide_offsets = []
        ansi_concatenated = ""
        wide_concatenated = ""

        byte_offset = 0
        for entry in self.ansi_strings:
            ansi_offsets.append(byte_offset)
            ansi_concatenated += entry + "\x00"
            byte_offset += len(entry) * 1

        logger.debug(f"Largest ANSI offset: {byte_offset}")

        byte_offset = 0
        for entry in self.wide_strings:
            wide_offsets.append(byte_offset)
            wide_concatenated += entry + "\x00"
            byte_offset += len(entry) * 2

        logger.debug(f"Largest WIDE offset: {byte_offset}")

        ansi_concatenated = ansi_concatenated.encode(encoding="utf-8")
        wide_concatenated = encode_no_bom(wide_concatenated, is_wide=True)

        # number names          DisplayEntryID              FName
        # names                 FName                       FName
        # numbered exports      NumberlessExportPath        AssetRegistryExportPath
        # exports               AssetRegistryExportPath     AssetRegistryExportPath
        # texts                 MarshalledText              FString
        # ansioffsets           uint32                      uint32
        # wide offsets          uin32                       uint32
        # ansistrings           String                      String
        # wide strings          WideString                  WideString
        # numberless pairs      NumberlessPair              FName + uint32
        # pairs                 NumberedPair                FName + uint32

        for table in [
            self.numberless_names,
            self.names,
            self.numberless_export_paths,
            self.export_paths,
            self.texts,
            ansi_offsets,
            wide_offsets,
            ansi_concatenated,
        ]:
            writer.write_int32(len(table) if table is not None else 0)

        writer.write_int32(int(len(wide_concatenated) / 2))

        for table in [
            self.numberless_pairs,
            self.numbered_pairs,
        ]:
            writer.write_int32(len(table) if table is not None else 0)

        if text_first:
            loc_text_byte_size = writer.tell()

            writer.write_uint32(0) # placeholder
            loc_before_writing_text = writer.tell()
            logger.debug(f"Writing TEXT tags to {hex(writer.tell())}")
            self.write_table(self.texts, writer.write_fstring)

            loc_after_writing_texts = writer.tell()

            text_section_size = loc_after_writing_texts - loc_before_writing_text

            writer.seek(loc_text_byte_size)
            writer.write_uint32(text_section_size) #overwrite bytesize placeholder
            writer.seek(loc_after_writing_texts)

            logger.debug(f"Wrote {text_section_size} bytes of text")

        logger.debug(f"Writing numberless names to {hex(writer.tell())}")
        self.write_table(self.numberless_names, fname_writer.write_fname)
        logger.debug(f"Writing numbered names to {hex(writer.tell())}")
        self.write_table(self.names, fname_writer.write_fname)
        logger.debug(f"Writing numberless paths to {hex(writer.tell())}")
        self.write_table(self.numberless_export_paths, fname_writer.write_export_path)
        logger.debug(f"Writing numbered paths to {hex(writer.tell())}")
        self.write_table(self.export_paths, fname_writer.write_export_path)

        if not text_first:
            logger.debug(f"Writing TEXT tags to {hex(writer.tell())}")
            self.write_table(self.texts, writer.write_fstring)

        logger.debug(f"Writing ANSI offset to {hex(writer.tell())}")
        self.write_table(ansi_offsets, writer.write_uint32)
        logger.debug(f"Writing WIDE offset to {hex(writer.tell())}")
        self.write_table(wide_offsets, writer.write_uint32)

        logger.debug(f"Writing ANSI texts to {hex(writer.tell())}")
        writer.write_bytes(ansi_concatenated)
        logger.debug(f"Writing WIDE texts to {hex(writer.tell())}")
        writer.write_bytes(wide_concatenated)

        self.write_table(self.numberless_pairs, fname_writer.write_key_val_pair)
        self.write_table(self.numbered_pairs, fname_writer.write_key_val_pair)

        writer.write_uint32(DATASTORE_END)



    @staticmethod
    def load_table(num_elements, element_getter):
        table = [
            element_getter()
            for _ in range(num_elements)
        ]

        return table

    @staticmethod
    def write_table(elements, element_writer):
        for element in elements:
            element_writer(element)

    def get_table_by_type(self, value_type: ValueTypes):
        tables_by_type = {
            ValueTypes.LocalizedText: self.texts,
            ValueTypes.AnsiString: self.ansi_strings,
            ValueTypes.WideString: self.wide_strings,
            ValueTypes.Name: self.names,
            ValueTypes.NumberlessName: self.numberless_names,
            ValueTypes.ExportPath: self.export_paths,
            ValueTypes.NumberlessExportPath: self.numberless_export_paths
        }
        table = tables_by_type.get(value_type)
        return table

    def get_hash_table_by_type(self, value_type: ValueTypes):
        table = self.hash_tables_by_type.get(value_type)
        return table

    def insert_value(self, val: str|SerializedString|FName|ExportPath, tag_type: ValueTypes):
        table = self.get_table_by_type(tag_type)
        hash_table = self.get_hash_table_by_type(tag_type)

        hasher = value_hashers.get(tag_type)
        hashed_value = hasher(val)

        if (val_idx := hash_table.get(hashed_value, None)) is not None:
            return FValueID(
                value_index=val_idx,
                value_type=tag_type,
            )


        new_index = len(table)

        table.append(val)
        hash_table[hashed_value] = new_index

        return FValueID(
            value_index=new_index,
            value_type=tag_type,
        )

    def register_map_pairs(self, tag_val_pairs: list[tuple[FName, FValueID]], has_numberless_keys: bool):

        table = self.numberless_pairs if has_numberless_keys else self.numbered_pairs

        new_idx = len(table)

        table.extend(tag_val_pairs)

        return TagMapHandle(
            has_numberless_keys=has_numberless_keys,
            handle_num=len(tag_val_pairs),
            pair_begin=new_idx,
        )

    def set_up_hashes(self):
        logger.debug("Setting up hashes")
        for val_type in ValueTypes:
            table = self.get_table_by_type(val_type)
            if table is None:
                continue
            hasher = value_hashers.get(val_type)
            hash_table = self.get_hash_table_by_type(val_type)

            for idx, val in enumerate(table):
                hash_table[hasher(val)] = idx

            assert len(self.hash_tables_by_type[val_type]) == len(table)


def hash_str(val: str):
    return CityHash64(val)

def fname_number_string(val: FName):
    return f"{val.name_idx}-{val.number}"

def export_path_number_string(val: ExportPath):
    return f"{fname_number_string(val.class_path.asset)}-{fname_number_string(val.class_path.package)}-{fname_number_string(val.package_name)}-{fname_number_string(val.object_name)}"

value_hashers = {
    ValueTypes.LocalizedText: lambda x: hash_str(x.string_view()),
    ValueTypes.AnsiString: hash_str,
    ValueTypes.WideString: hash_str,
    ValueTypes.Name: lambda x: hash_str(fname_number_string(x)),
    ValueTypes.NumberlessName: lambda x: hash_str(fname_number_string(x)),
    ValueTypes.ExportPath: lambda x: hash_str(export_path_number_string(x)),
    ValueTypes.NumberlessExportPath: lambda x: hash_str(export_path_number_string(x))
}