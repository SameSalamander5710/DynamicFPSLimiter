# src/core/version.py
# Single source of truth for the DynamicFPSLimiter version.

VERSION = (5, 0, 1, 0)  # major, minor, patch, build

_APP_NAME = "DynamicFPSLimiter"
_COMPANY_NAME = "SameSalamander5710"


def full_version():
    """Full dotted version, e.g. ``5.0.0.0`` (matching ``VERSION``)."""
    return ".".join(str(part) for part in VERSION)


def display_version():
    """Short display form shown in the GUI (e.g. ``v5.0.0``)."""
    return "v" + ".".join(str(part) for part in VERSION[:3])


def version_file_text():
    """PyInstaller ``--version-file`` content (written to ``version.txt``).

    PyInstaller deserializes this with ``eval()`` against its versioninfo
    classes, so it must stay a bare expression referencing only those names.
    """
    return (
        "# version.txt\n"
        "\n"
        "VSVersionInfo(\n"
        "  ffi=FixedFileInfo(\n"
        f"    filevers={VERSION},\n"
        f"    prodvers={VERSION},\n"
        "    mask=0x3f,\n"
        "    flags=0x0,\n"
        "    OS=0x4,\n"
        "    fileType=0x1,\n"
        "    subtype=0x0,\n"
        "    date=(0, 0)\n"
        "  ),\n"
        "  kids=[\n"
        "    StringFileInfo(\n"
        "      [\n"
        "        StringTable(\n"
        "          '040904B0',\n"
        "          [\n"
        f"            StringStruct('CompanyName', '{_COMPANY_NAME}'),\n"
        f"            StringStruct('FileDescription', '{_APP_NAME}'),\n"
        f"            StringStruct('FileVersion', '{full_version()}'),\n"
        f"            StringStruct('InternalName', '{_APP_NAME}'),\n"
        f"            StringStruct('OriginalFilename', '{_APP_NAME}.exe'),\n"
        f"            StringStruct('ProductName', '{_APP_NAME}'),\n"
        f"            StringStruct('ProductVersion', '{full_version()}')\n"
        "          ]\n"
        "        )\n"
        "      ]\n"
        "    ),\n"
        "    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n"
        "  ]\n"
        ")\n"
    )


def write_version_txt(path):
    """Regenerate the PyInstaller version resource at ``path`` from VERSION."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(version_file_text())