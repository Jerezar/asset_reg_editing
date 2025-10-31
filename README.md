# AssetReg
Limited command line tool to convert an asset registry to editable json and back.

Made by consulting the UE5.2 files as well as the workings of existing tools
such as [CUE4Parse](https://github.com/FabianFG/CUE4Parse/tree/b1fedf03682479511ed966093e1abe4060ace36d).

Intended for use in the development of the ["Beyond Hell"](https://github.com/RemnantETS/Remnant2-BeyondHell) mod for Remnant 2, and as such hardcoded to a few assumptions,
such as the registry using the serialization version 17, or there being no dependencies or package data in the registry.

run `poetry install` to make the commands available

`poetry asset_reg <subcommand>` is the actual command; with the subcommands `bin_to_json` and `json_to_bin`
both taking a source file and allowing an optional output file with the `-o` option.

The editable json wraps all tag values of assets in a type marker, taking the form of the typename,
followed by the actual value in round brackets.

## Tag types
*NOTE: When converting back into binary the tag types are currently not scrutinized, so make sure to use the right one.*
- `ANSI` / `WIDE`: most values are saved as string, ANSI being normal ASCII and WIDE anything that has characters outside that range
- `TEXT`
- `NAME` / `NAME__NO_NUM`: FName, with or without instance number respectively
- `PATH` / `PATH__NO_NUM`: Export path, the latter only if all constituent names have no number
