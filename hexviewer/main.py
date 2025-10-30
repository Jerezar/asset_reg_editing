import logging

import click

from hexviewer.read_asset_reg import registry_bin_to_json, registry_json_to_bin

logger = logging.getLogger(__name__)


@click.group(
    "asset_reg"
)
@click.option(
    "verbosity",
    "--verbose",
    "-v",
    count=True
)
def cli(verbosity: int):
    debug_levels = [
        logging.WARN,
        logging.INFO,
        logging.DEBUG
    ]
    logging.basicConfig(level=debug_levels[min(verbosity, len(debug_levels)-1)])


cli.add_command(registry_bin_to_json)
cli.add_command(registry_json_to_bin)