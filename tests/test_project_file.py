import sys
from pathlib import Path
from datetime import datetime
import zipfile
import pytest

# Support src/ layout if pytest isn't already configured for it
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ProjectFile import ProjectFile  # noqa: E402


def test_project_file_from_zipinfo_extracts_name_type_size_and_modified(tmp_path: Path) -> None:
    zpath = tmp_path / "sample.zip"
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("folder/sub/file.TXT", "content")

    with zipfile.ZipFile(zpath, "r") as zf:
        info = zf.getinfo("folder/sub/file.TXT")
        pf = ProjectFile(info, parent_folder=None)

    assert pf.file_name == "file.TXT"
    assert pf.size == len("content")
    assert isinstance(pf.last_modified, datetime)
    assert pf.file_type == "txt"  # extension lowercased
    assert pf.parent_folder is None
    assert pf.date_created is None
    assert pf.last_accessed is None
    assert "ProjectFile(" in repr(pf)


def test_project_file_raises_on_directory_entry(tmp_path: Path) -> None:
    zpath = tmp_path / "dirs.zip"
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("dir_only/", "")

    with zipfile.ZipFile(zpath, "r") as zf:
        dir_info = zf.getinfo("dir_only/")
        assert dir_info.is_dir()
        with pytest.raises(ValueError):
            ProjectFile(dir_info, parent_folder=None)


def test_project_file_sets_parent_folder_reference(tmp_path: Path) -> None:
    class DummyParent:
        pass

    parent = DummyParent()

    zpath = tmp_path / "p.zip"
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a/b/c.py", "print(1)")

    with zipfile.ZipFile(zpath, "r") as zf:
        info = zf.getinfo("a/b/c.py")
        pf = ProjectFile(info, parent_folder=parent)

    assert pf.parent_folder is parent
