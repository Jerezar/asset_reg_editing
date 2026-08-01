import json
import jmespath
from pathlib import Path

import click

@click.command(
    "merge_json_regs",
    help="Merges several JSON registries into one."
)
@click.argument(
    "input_files",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, readable=True, resolve_path=True, path_type=Path),
    nargs=-1,
)
@click.option(
    "output_path",
    "--output",
    "-o",
    type=click.Path(exists=False, dir_okay=False, file_okay=True, writable=True, resolve_path=True, path_type=Path),
    default=None
)
def merge_json_regs(input_files: tuple[Path, ...], output_path: Path | None):
    main_input = input_files[0]

    json_filter = jmespath.compile("""
    {
        "Header": [0].Header,
        "State": {
            "Assets": [*].State.Assets[],
            "Dependencies": `[]`,
            "Packages": `[]`,
            "Options": [0].State.Options
        }
    }
    """)

    if output_path is None:
        output_path = main_input.with_stem(main_input.stem + "_merged").with_suffix(".json")

    registries = []
    for input_file in input_files:
        with input_file.open("r") as reader:
            registries.append(json.load(reader))

    registry: dict = json_filter.search(registries)

    with output_path.open("w") as writer:
        writer.write(
            json.dumps(
                registry,
                indent=2
            )
        )