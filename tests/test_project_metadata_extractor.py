from datetime import datetime
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor


def mock_file_categorizer(monkeypatch):
   """Prevents FileCategorizer from running real logic during tests."""
   class DummyCategorizer:
       def compute_metrics(self, files):


           return {
               "counts": {"code": len(files)},
               "percentages": {"code": 100.0}
           }
   monkeypatch.setattr(
       "src.analyzers.ProjectMetadataExtractor.FileCategorizer",
       DummyCategorizer
   )


class DummyFile:
   def __init__(self, size, modified):
       self.size = size
       self.last_modified = modified
       self.name = "dummy.txt"
       self.full_path = "dummy.txt"


class DummyFolder:
   def __init__(self, children=None, subdir=None, name ="dummy"):
       self.children = children or []
       self.subdir = subdir or []
       self.name = name


def test_basic_metadata_extraction():
   file1 = DummyFile(1024, datetime(2023, 3, 7))
   file2 = DummyFile(12350, datetime(2019, 1, 11))
   file3 = DummyFile(4096, datetime(2025, 9, 25))


   root = DummyFolder(children = [file1, file2, file3], name="root")
   extractor = ProjectMetadataExtractor(root)
   summary = extractor.extract_metadata()["project_metadata"]


   assert summary is not None, "Extractor returned None"


   expected_total_kb = round((1024 + 12350 + 4096)/1024, 2)
   expected_days = (datetime(2025, 9, 25) - datetime(2019, 1, 11)).days
   expected_avg_kb = round(expected_total_kb/3, 2)


   assert summary["total_files"] == 3
   assert round(summary["total_size_kb"], 2) == expected_total_kb
   assert summary["duration_days"] == expected_days
   assert summary["average_file_size_kb"] == expected_avg_kb


def test_empty_folder_returns_none(capsys):
   root = DummyFolder(children = [])
   extractor = ProjectMetadataExtractor(root)


   result = extractor.extract_metadata()


   captured = capsys.readouterr()
   assert "No files" in captured.out
   assert result is None


def test_nested_folders_are_counted():
   f1 = DummyFile(500, datetime(2022, 5, 10))
   f2 = DummyFile(1500, datetime(2023, 6, 1))
   f3 = DummyFile(2500, datetime(2024, 7, 15))


   subfolder = DummyFolder(children=[f2, f3], name = "subfolder")


   root = DummyFolder(children=[f1], subdir=[subfolder], name="root")


   extractor = ProjectMetadataExtractor(root)
   summary = extractor.extract_metadata()["project_metadata"]


   assert summary["total_files"] == 3


   total_size = 4500
   expected_kb = round(total_size/1024, 2)
   expected_days = (datetime(2024, 7, 15) - datetime(2022, 5, 10)).days


   assert summary["duration_days"] == expected_days
   assert round(summary["total_size_kb"], 2) == expected_kb


def test_missing_timestamps_ignored():
   f1 = DummyFile(1024, None)
   f2 = DummyFile(2048, datetime(2025, 10, 12))


   root = DummyFolder(children=[f1, f2], name="root")
   extractor = ProjectMetadataExtractor(root)
   full_summary = extractor.extract_metadata()


   # ✅ project-level summary is nested
   project_summary = full_summary["project_metadata"]
