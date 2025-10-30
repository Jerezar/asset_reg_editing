import json
import logging
import sys
from itertools import batched
from logging import DEBUG
from pathlib import Path

import click

from hexviewer.asset_registry_ue5.binary_conversion.read_binary_file import asset_registry_from_file
from hexviewer.asset_registry_ue5.binary_conversion.write_binary_file import asset_registry_to_binary_file
from hexviewer.asset_registry_ue5.json_conversion.make_editable_json import make_editable_json
from hexviewer.asset_registry_ue5.json_conversion.read_editable_json import load_registry_from_json
from hexviewer.asset_registry_ue5.readers.binary_reader import BinaryReader
from hexviewer.asset_registry_ue5.readers.binary_writer import BinaryWriter

@click.command(
    "bin_to_json",
    help="Converts the specified binary file into editable json."
)
@click.argument(
    "input_file",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, readable=True, resolve_path=True, path_type=Path),
)
@click.option(
    "output_path",
    "--output",
    "-o",
    type=click.Path(exists=False, dir_okay=False, file_okay=True, writable=True, resolve_path=True, path_type=Path),
    default=None
)
def registry_bin_to_json(input_file: Path, output_path: Path | None, file_byte_order=sys.byteorder):
    if output_path is None:
        output_path = input_file.with_stem(input_file.stem + "_parsed").with_suffix(".json")

    with input_file.open("rb") as reader:
        binaries = BinaryReader(reader, file_byte_order)
        registry = asset_registry_from_file(binaries)

    with output_path.open("w") as writer:
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

@click.command(
    "json_to_bin",
    help="Converts the specified json file into a binary file."
)
@click.argument(
    "input_file",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, readable=True, resolve_path=True, path_type=Path),
)
@click.option(
    "output_path",
    "--output",
    "-o",
    type=click.Path(exists=False, dir_okay=False, file_okay=True, writable=True, resolve_path=True, path_type=Path),
    default=None
)
def registry_json_to_bin(input_file: Path, output_path: Path | None, file_byte_order=sys.byteorder):
    if output_path is None:
        output_path = input_file.with_stem(input_file.stem + "_encoded").with_suffix(".bin")

    with input_file.open("r") as reader:
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


