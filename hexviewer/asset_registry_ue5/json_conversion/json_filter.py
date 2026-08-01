import jmespath
from pathlib import Path

def apply_json_filter(json_registry: dict, filter_file: Path) -> dict:
    with filter_file.open() as reader:
        json_filter = jmespath.compile(reader.read())

    return json_filter.search(json_registry)