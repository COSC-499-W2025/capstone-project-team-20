from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional
from zipfile import ZipInfo


class ProjectFile:
    """
    Represents a file in a project tree (sibling to ProjectFolder nodes).
    Designed to be constructed from a zipfile.ZipInfo entry.

    Notes:
    - Only file entries are supported at construction time; directory entries will raise ValueError.
    - ZIP archives provide last modified time (ZipInfo.date_time) and size (ZipInfo.file_size).
      Created and last accessed times are not preserved and are left as None.

    References:
    - zipfile module: https://docs.python.org/3/library/zipfile.html
    """

    file_name: str
    parent_folder: Optional[object]
    date_created: Optional[datetime]
    last_modified: Optional[datetime]
    last_accessed: Optional[datetime]
    file_type: str
    size: int

    def __init__(self, file: ZipInfo, parent_folder: Optional[object]) -> None:
        if file.is_dir():
            raise ValueError("ProjectFile requires a file entry (got a directory).")
        
        self.full_path = file.filename #Full path inside ZIP!

        # Base name from ZIP-internal path (always uses '/')
        name = file.filename.split("/")[-1]
        if not name:
            raise ValueError("Invalid ZipInfo: could not extract file name.")

        self.file_name = name
        self.parent_folder = parent_folder

        # Metadata available from ZipInfo
        self.size = int(getattr(file, "file_size", 0))
        self.last_modified = datetime(*file.date_time)

        # Infer a simple 'type' from the file extension (lowercased, no leading dot)
        self.file_type = Path(name).suffix.lower().lstrip(".")

        # Not provided by ZIP format; reserved for future enrichment
        self.date_created = None
        self.last_accessed = None

    def __repr__(self) -> str:
        return (
            f"ProjectFile(file_name={self.file_name!r}, size={self.size}, "
            f"file_type={self.file_type!r}, last_modified={self.last_modified!r})"
        )
