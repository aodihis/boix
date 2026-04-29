def detect_onix_version(file_path: str) -> str:
    """Reads only first 512 bytes to detect ONIX version from the release attribute."""
    with open(file_path, "rb") as f:
        header = f.read(512).decode("utf-8", errors="replace")

    if 'release="3.1"' in header:
        return "3.1"
    if 'release="3.0"' in header:
        return "3.0"
    if 'release="2.1"' in header:
        return "2.1"

    # Default to 3.0 when no release attribute found
    return "3.0"
