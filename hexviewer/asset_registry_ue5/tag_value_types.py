from enum import IntEnum, auto


class ValueTypes(IntEnum):
    AnsiString = 0
    WideString = auto()
    NumberlessName = auto()
    Name = auto()
    NumberlessExportPath = auto()
    ExportPath = auto()
    LocalizedText = auto()
