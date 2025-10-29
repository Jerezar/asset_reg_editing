import re

from cityhash import CityHash64

from hexviewer.asset_registry_ue5.unreal_types import SerializedString, FName

NUMBERED_FNAME_PATTERN = re.compile(
    r"^(.*)___(\d+)$",
)

class NameMapper:
    HASH_VERSION = 0xC1640000
    def __init__(self, names: list[SerializedString] | None = None):
        self.names: dict[int, tuple[int, SerializedString]] = {}
        self.names_by_idx: list[SerializedString] = []

        if names is None:
            names = []

        for name in names:
            self.names[self.make_hash(name.string_view())] = len(self.names), name
            self.names_by_idx.append(name)


    def fname_from_string(self, name: str) -> FName | None:
        if name is None:
            return None

        name, number = self.read_numbered_fname(name)
        key = self.make_hash(name)

        if (indexed_name := self.names.get(key)) is not None:
            idx , _ = indexed_name
            return FName(
                name_idx=idx,
                number=number,
            )

        new_idx = len(self.names)
        name_data = SerializedString.from_string(name)

        self.names[key] = new_idx, name_data
        self.names_by_idx.append(name_data)

        return FName(
            name_idx=new_idx,
            number=number,
        )

    def string_from_fname(self, name: FName) -> str | None:
        if name is None:
            return None

        name_serialized = self.names_by_idx[name.name_idx]
        name_parsed = name_serialized.string_view()

        if not (name.number == FName.NO_NUMBER):
            name_parsed+=f"___{name.number-1}"

        return name_parsed


    def read_numbered_fname(self, name: str):
        if match := re.fullmatch(NUMBERED_FNAME_PATTERN, name):
            name = match.group(1)
            number = int(match.group(2)) + 1
        else:
            number = FName.NO_NUMBER

        return name, number


    def make_hash(self, name:str):
        return CityHash64(name)