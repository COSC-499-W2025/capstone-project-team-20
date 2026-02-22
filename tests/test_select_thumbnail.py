import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import shutil
import os
from src.models.Project import Project
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager


class TestSelectThumbnail:
    """Focused tests for the select_thumbnail method."""

    @pytest.fixture
    def real_cli(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config_manager = Mock(spec=ConfigManager)
        cli = ProjectAnalyzer(
            config_manager=config_manager,
            root_folders=[],
            zip_path=tmp_path / "test.zip"
        )
        yield cli

    @pytest.fixture
    def sample_projects(self, real_cli):
        projects = []
        for i in range(3):
            project = Project(
                name=f"Test Project {i+1}",
                file_path=f"/path/to/project{i+1}",
                resume_score=float(5 + i)
            )
            real_cli.project_manager.set(project)
            projects.append(project)
        return projects

    @pytest.fixture
    def real_images(self, tmp_path):
        images = {}
        jpg = tmp_path / "test.jpg"
        jpg.write_bytes(b'\xff\xd8\xff\xe0JFIF' + b'\x00' * 50 + b'\xff\xd9')
        images['jpg'] = jpg
        png = tmp_path / "test.png"
        png.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 50)
        images['png'] = png
        return images

    def test_no_projects_available(self, real_cli, capsys):
        with patch('builtins.input'):
            real_cli.select_thumbnail()
        captured = capsys.readouterr()
        assert "No scored projects available" in captured.out

    def test_user_cancels_at_project_selection(self, real_cli, sample_projects, capsys):
        with patch('builtins.input', return_value='q'):
            real_cli.select_thumbnail()
        captured = capsys.readouterr()
        assert "Returning to main menu" in captured.out

    def test_user_provides_empty_path(self, real_cli, sample_projects, capsys):
        inputs = ['1', '']
        with patch('builtins.input', side_effect=inputs):
            real_cli.select_thumbnail()
        captured = capsys.readouterr()
        assert "No path provided" in captured.out

    def test_user_provides_whitespace_only_path(self, real_cli, sample_projects, capsys):
        inputs = ['1', '   \t  ']
        with patch('builtins.input', side_effect=inputs):
            real_cli.select_thumbnail()
        captured = capsys.readouterr()
        assert "No path provided" in captured.out

    def test_nonexistent_file_path(self, real_cli, sample_projects, capsys):
        inputs = ['1', '/fake/path/image.jpg']
        with patch('builtins.input', side_effect=inputs):
            real_cli.select_thumbnail()
        captured = capsys.readouterr()
        assert "File not found" in captured.out

    def test_path_to_directory_not_file(self, real_cli, sample_projects, tmp_path, capsys):
        directory = tmp_path / "folder"
        directory.mkdir()
        inputs = ['1', str(directory)]
        with patch('builtins.input', side_effect=inputs):
            real_cli.select_thumbnail()
        captured = capsys.readouterr()
        assert "Path is not a file" in captured.out

    @pytest.mark.parametrize("extension,content", [
        ('.txt', b'abc'),
        ('.pdf', b'%PDF'),
        ('.zip', b'PK\x03\x04'),
    ])
    def test_invalid_file_extensions(self, real_cli, sample_projects, tmp_path, extension, content, capsys):
        invalid = tmp_path / f"file{extension}"
        invalid.write_bytes(content)
        inputs = ['1', str(invalid)]
        with patch('builtins.input', side_effect=inputs):
            real_cli.select_thumbnail()
        captured = capsys.readouterr()
        assert "Invalid image format" in captured.out

    def test_thumbnails_directory_created_automatically(self, real_cli, sample_projects, real_images, tmp_path):
        thumbnails_dir = tmp_path / "thumbnails"
        assert not thumbnails_dir.exists()
        inputs = ['1', str(real_images['jpg'])]
        with patch('builtins.input', side_effect=inputs):
            real_cli.select_thumbnail()
        assert thumbnails_dir.exists()

    def test_permission_error_when_copying(self, real_cli, sample_projects, real_images, tmp_path, capsys):
        thumbnails_dir = tmp_path / "thumbnails"
        thumbnails_dir.mkdir()
        os.chmod(thumbnails_dir, 0o444)
        try:
            inputs = ['1', str(real_images['jpg'])]
            with patch('builtins.input', side_effect=inputs):
                real_cli.select_thumbnail()
            captured = capsys.readouterr()
            assert "Permission denied" in captured.out
            project = real_cli.project_manager.get(sample_projects[0].id)
            assert project.thumbnail is None
        finally:
            os.chmod(thumbnails_dir, 0o755)

    def test_disk_full_simulation(self, real_cli, sample_projects, real_images, capsys):
        with patch('shutil.copy', side_effect=OSError("No space left on device")):
            inputs = ['1', str(real_images['jpg'])]
            with patch('builtins.input', side_effect=inputs):
                real_cli.select_thumbnail()
        captured = capsys.readouterr()
        assert "Error copying file" in captured.out

    def test_invalid_project_selection_number(self, real_cli, sample_projects, capsys):
        inputs = ['999', 'q']
        with patch('builtins.input', side_effect=inputs):
            real_cli.select_thumbnail()
        captured = capsys.readouterr()
        assert "Invalid project number" in captured.out

    def test_non_numeric_project_selection(self, real_cli, sample_projects, capsys):
        inputs = ['abc', 'q']
        with patch('builtins.input', side_effect=inputs):
            real_cli.select_thumbnail()
        captured = capsys.readouterr()
        assert "Invalid input" in captured.out

    def test_uppercase_extension_accepted(self, real_cli, sample_projects, tmp_path, capsys):
        img = tmp_path / "IMAGE.JPG"
        img.write_bytes(b'\xff\xd8\xff\xe0JFIF' + b'\x00' * 50 + b'\xff\xd9')
        inputs = ['1', str(img)]
        with patch('builtins.input', side_effect=inputs):
            real_cli.select_thumbnail()
        captured = capsys.readouterr()
        assert "successfully added" in captured.out

    def test_correct_thumbnail_filename_format(self, real_cli, sample_projects, real_images, capsys):
        sorted_projects = real_cli.get_projects_sorted_by_score()
        p = sorted_projects[0]
        inputs = ['1', str(real_images['jpg'])]
        with patch('builtins.input', side_effect=inputs):
            real_cli.select_thumbnail()
        updated = real_cli.project_manager.get(p.id)
        expected = f"project_{p.id}_thumb.jpg"
        assert expected in updated.thumbnail

    def test_different_projects_get_different_thumbnails(self, real_cli, sample_projects, real_images):
        sorted_projects = real_cli.get_projects_sorted_by_score()
        inputs1 = ['1', str(real_images['jpg'])]
        with patch('builtins.input', side_effect=inputs1):
            real_cli.select_thumbnail()
        inputs2 = ['2', str(real_images['png'])]
        with patch('builtins.input', side_effect=inputs2):
            real_cli.select_thumbnail()
        p1 = real_cli.project_manager.get(sorted_projects[0].id)
        p2 = real_cli.project_manager.get(sorted_projects[1].id)
        assert p1.thumbnail != p2.thumbnail

    def test_replacing_existing_thumbnail(self, real_cli, sample_projects, real_images, capsys):
        sorted_projects = real_cli.get_projects_sorted_by_score()
        p = sorted_projects[0]

        # First thumbnail
        inputs1 = ['1', str(real_images['jpg'])]
        with patch('builtins.input', side_effect=inputs1):
            real_cli.select_thumbnail()

        first_thumb = Path(real_cli.project_manager.get(p.id).thumbnail)
        first_size = first_thumb.stat().st_size

        # Second thumbnail (different type)
        inputs2 = ['1', str(real_images['png'])]
        with patch('builtins.input', side_effect=inputs2):
            real_cli.select_thumbnail()

        second_thumb = Path(real_cli.project_manager.get(p.id).thumbnail)
        second_size = second_thumb.stat().st_size

        assert first_thumb != second_thumb
        assert second_thumb.exists()
        assert first_size != second_size
