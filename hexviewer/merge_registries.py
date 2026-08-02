import json
import jmespath
from pathlib import Path

import jmespath.functions as functions
import jmespath.exceptions as jmes_exceptions

import click

class CustomFunctions(functions.Functions):
    @functions.signature({"types": ["array"]}, {"types": ["expref"]})
    def _func_keep_first_occurrence(self, entries: list, expref):
        keyfunc = self._create_key_func(expref,
                                        ['number', 'string'],
                                        'keep_first_occurrence')
        uniques = set()
        mask = []
        for entry in entries:
            mapped = keyfunc(entry)
            if not mapped in uniques:
                mask.append(entry)
            uniques.add(mapped)
        return mask

    def _create_key_func(self, expref, allowed_types, function_name):
        def keyfunc(x):
            result = expref.visit(expref.expression, x)
            actual_typename = type(result).__name__
            jmespath_type = self._convert_to_jmespath_type(actual_typename)
            if jmespath_type not in allowed_types:
                raise jmes_exceptions.JMESPathTypeError(
                    function_name, result, jmespath_type, allowed_types)
            return result

        return keyfunc


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
    input_files = reversed(input_files)

    options = jmespath.Options(custom_functions=CustomFunctions())

    if output_path is None:
        output_path = main_input.with_stem(main_input.stem + "_merged").with_suffix(".json")

    registries = []
    for input_file in input_files:
        with input_file.open("r") as reader:
            registries.append(json.load(reader))

    registry: dict = jmespath.search("""
    {
        "Header": [-1].Header,
        "State": {
            "Assets": keep_first_occurrence( [*].State.Assets[], &join(`,`, [PackageName, AssetName])),
            "Dependencies": `[]`,
            "Packages": `[]`,
            "Options": [-1].State.Options
        }
    }
    """, registries, options=options)

    with output_path.open("w") as writer:
        writer.write(
            json.dumps(
                registry,
                indent=2
            )
        )