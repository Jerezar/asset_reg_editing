from hexviewer.asset_registry_ue5.tag_value_types import ValueTypes

MARKERS_BY_TYPE: dict[ValueTypes, str] = {
    ValueTypes.AnsiString: "ANSI",
    ValueTypes.WideString: "WIDE",
    ValueTypes.NumberlessName: "NAME__NO_NUM",
    ValueTypes.Name: "NAME",
    ValueTypes.NumberlessExportPath: "PATH__NO_NUM",
    ValueTypes.ExportPath: "PATH",
    ValueTypes.LocalizedText: "TEXT",
}

TYPES_BY_MARKER: dict[str, ValueTypes] = {
    v: k for k, v in MARKERS_BY_TYPE.items()
}

assert len(MARKERS_BY_TYPE) == len(TYPES_BY_MARKER)

