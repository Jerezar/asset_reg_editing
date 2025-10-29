def encode_no_bom(val: str, is_wide: bool):
    string_data = val.encode("utf-16" if is_wide else "utf-8")
    if is_wide:
        string_data = bytes(string_data[2:])

    return string_data