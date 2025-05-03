from prompt_toolkit.styles import Style


def read_style(s: str) -> Style:
    styles = {}

    for entry in s.split(" "):
        if not entry:
            continue

        parts = entry.split(":")

        if not len(parts) == 2:
            raise ValueError(f"Invalid style: '{entry}'")

        styles[parts[0]] = parts[1]

    return Style.from_dict(styles)
