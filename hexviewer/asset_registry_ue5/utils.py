def encode_no_bom(val: str, is_wide: bool):
    string_data = val.encode("utf-16" if is_wide else "utf-8")
    if is_wide:
        if any([
            string_data.startswith(pref)
            for pref in ( bytes((0xFE, 0xFF)), bytes((0xFF, 0xFE)) )
        ]):
            string_data = bytes(string_data[2:])

    return string_data