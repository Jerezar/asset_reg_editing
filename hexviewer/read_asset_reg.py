import json
import logging
import sys
from itertools import batched
from logging import DEBUG
from pathlib import Path
from hexviewer.asset_registry_ue5.binary_conversion.read_binary_file import asset_registry_from_file
from hexviewer.asset_registry_ue5.binary_conversion.write_binary_file import asset_registry_to_binary_file
from hexviewer.asset_registry_ue5.json_conversion.make_editable_json import make_editable_json
from hexviewer.asset_registry_ue5.json_conversion.read_editable_json import load_registry_from_json
from hexviewer.asset_registry_ue5.readers.binary_reader import BinaryReader
from hexviewer.asset_registry_ue5.readers.binary_writer import BinaryWriter


def registry_bin_to_json(registry_file: Path, registry_out: Path, file_byte_order=sys.byteorder):
    with registry_file.open("rb") as reader:
        binaries = BinaryReader(reader, file_byte_order)
        registry = asset_registry_from_file(binaries)

    with registry_out.open("w") as writer:
        writer.write(
            json.dumps(make_editable_json(registry), indent=2)
        )

def load_write_json_test(input_json: Path, output_path: Path):
    with input_json.open("r") as reader:
        registry = load_registry_from_json(json.load(reader))

    with output_path.open("w") as writer:
        writer.write(
            json.dumps(make_editable_json(registry), indent=2)
        )

def registry_json_to_bin(input_json: Path, output_path: Path, file_byte_order=sys.byteorder):
    with input_json.open("r") as reader:
        registry = load_registry_from_json(json.load(reader))

    with output_path.open("wb") as writer:
        binaries = BinaryWriter(writer, file_byte_order)
        asset_registry_to_binary_file(registry, binaries)


def load_write_bin_test(input_file: Path, output_path: Path, file_byte_order=sys.byteorder):
    with input_file.open("rb") as reader:
        binaries = BinaryReader(reader, file_byte_order)
        registry = asset_registry_from_file(binaries)

    with output_path.open("wb") as writer:
        binaries = BinaryWriter(writer, file_byte_order)
        asset_registry_to_binary_file(registry, binaries)



BYTES_PER_LINE = 8
def show_hex(registry_file: Path, n, offset = 0, ):
    with registry_file.open("rb") as reader:
        reader.seek(offset)
        byte_data = reader.read(n)

        for batch in batched(byte_data, BYTES_PER_LINE):
            print("  ".join([f"{b:02x}" for b in batch]) + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=DEBUG)
    reg_file = Path(r"F:\game extraction\FModel\Output\Exports\Remnant2\AssetRegistry.bin")
    test_bin_rewrite = reg_file.with_stem("bin_registry_rewrite")

    reg_json_file = reg_file.with_stem("parsed_registry").with_suffix(".json")
    test_json_rewrite = reg_json_file.with_stem("parsed_load_write_test")

    #registry_bin_to_json(reg_file, reg_json_file)
    registry_json_to_bin(reg_json_file, test_bin_rewrite)
    registry_bin_to_json(test_bin_rewrite, test_json_rewrite)

