from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

from utils.analyze_repos import (
    validate_zipped_directory,
    analyze_all_zips,
    run_analysis_workflow,
)
from src.Project import Project


class TestValidateZippedDirectory:
    """Tests for the validate_zipped_directory function."""

    def test_returns_true_for_existing_directory(self, tmp_path: Path):
        """Verify validation passes for an existing directory."""
        assert validate_zipped_directory(tmp_path) is True

    def test_returns_false_for_nonexistent_directory(self, tmp_path: Path):
        """Verify validation fails for a missing directory."""
        nonexistent = tmp_path / "does_not_exist"
        assert validate_zipped_directory(nonexistent) is False


class TestAnalyzeAllZips:
    """Tests for the analyze_all_zips function."""

    def test_successful_analysis_increments_success_count(self, tmp_path: Path):
        """Verify successful analysis is counted correctly."""
        # Arrange
        zip_file = tmp_path / "test_repo.zip"
        zip_file.touch()
        
        mock_project = Project(name="test_repo", authors=["dev@test.com"], collaboration_status="individual")
        mock_analyzer = Mock()
        mock_analyzer.run_analysis_from_path.return_value = [mock_project]
        
        with patch('utils.analyze_repos.extract_zip') as mock_extract:
            mock_extract.return_value = str(tmp_path / "extracted")
            (tmp_path / "extracted").mkdir()
            
            # Act
            success, fail, projects = analyze_all_zips([zip_file], mock_analyzer)
        
        # Assert
        assert success == 1
        assert fail == 0
        assert len(projects) == 1
        assert projects[0].name == "test_repo"

    def test_failed_analysis_increments_fail_count(self, tmp_path: Path):
        """Verify failed analysis is counted correctly."""
        # Arrange
        zip_file = tmp_path / "bad_repo.zip"
        zip_file.touch()
        
        mock_analyzer = Mock()
        mock_analyzer.run_analysis_from_path.side_effect = Exception("Extraction failed")
        
        with patch('utils.analyze_repos.extract_zip') as mock_extract:
            mock_extract.side_effect = Exception("Bad zip")
            
            # Act
            success, fail, projects = analyze_all_zips([zip_file], mock_analyzer)
        
        # Assert
        assert success == 0
        assert fail == 1
        assert len(projects) == 0

    def test_no_git_repo_found_counts_as_failure(self, tmp_path: Path):
        """Verify repos without .git directory are counted as failures."""
        # Arrange
        zip_file = tmp_path / "no_git_repo.zip"
        zip_file.touch()
        
        mock_analyzer = Mock()
        mock_analyzer.run_analysis_from_path.return_value = []  # No projects found
        
        with patch('utils.analyze_repos.extract_zip') as mock_extract:
            mock_extract.return_value = str(tmp_path / "extracted")
            (tmp_path / "extracted").mkdir()
            
            # Act
            success, fail, projects = analyze_all_zips([zip_file], mock_analyzer)
        
        # Assert
        assert success == 0
        assert fail == 1

    def test_temp_directory_cleaned_up_on_success(self, tmp_path: Path):
        """Verify temporary directories are removed after successful analysis."""
        # Arrange
        zip_file = tmp_path / "test_repo.zip"
        zip_file.touch()
        temp_extract_dir = tmp_path / "temp_extract"
        temp_extract_dir.mkdir()
        
        mock_analyzer = Mock()
        mock_analyzer.run_analysis_from_path.return_value = [Project(name="test")]
        
        with patch('utils.analyze_repos.extract_zip') as mock_extract:
            mock_extract.return_value = str(temp_extract_dir)
            
            # Act
            analyze_all_zips([zip_file], mock_analyzer)
        
        # Assert
        assert not temp_extract_dir.exists()

    def test_temp_directory_cleaned_up_on_failure(self, tmp_path: Path):
        """Verify temporary directories are removed even after failed analysis."""
        # Arrange
        zip_file = tmp_path / "test_repo.zip"
        zip_file.touch()
        temp_extract_dir = tmp_path / "temp_extract"
        temp_extract_dir.mkdir()
        
        mock_analyzer = Mock()
        mock_analyzer.run_analysis_from_path.side_effect = Exception("Analysis failed")
        
        with patch('utils.analyze_repos.extract_zip') as mock_extract:
            mock_extract.return_value = str(temp_extract_dir)
            
            # Act
            analyze_all_zips([zip_file], mock_analyzer)
        
        # Assert
        assert not temp_extract_dir.exists()


class TestRunAnalysisWorkflow:
    """Integration-style tests for the main workflow function."""

    def test_exits_early_when_zipped_dir_missing(self, tmp_path: Path):
        """Verify workflow exits gracefully when zipped_repos doesn't exist."""
        # Arrange
        nonexistent = str(tmp_path / "nonexistent")
        
        # Act & Assert (should not raise)
        run_analysis_workflow(zipped_dir=nonexistent)

    def test_exits_early_when_no_zip_files(self, tmp_path: Path):
        """Verify workflow exits gracefully when no .zip files exist."""
        # Arrange - empty directory
        # Act & Assert (should not raise)
        run_analysis_workflow(zipped_dir=str(tmp_path))

    @patch('utils.analyze_repos.GitRepoAnalyzer')
    @patch('utils.analyze_repos.ProjectManager')
    @patch('utils.analyze_repos.RepoFinder')
    @patch('utils.analyze_repos.extract_zip')
    def test_full_workflow_processes_multiple_zips(
        self, 
        mock_extract, 
        mock_finder_cls, 
        mock_manager_cls, 
        mock_analyzer_cls,
        tmp_path: Path
    ):
        """Verify workflow correctly processes multiple zip files."""
        # Arrange
        (tmp_path / "repo1.zip").touch()
        (tmp_path / "repo2.zip").touch()
        
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        mock_extract.return_value = str(extract_dir)
        
        mock_project = Project(name="test", authors=["a@b.com"])
        mock_analyzer = Mock()
        mock_analyzer.run_analysis_from_path.return_value = [mock_project]
        mock_analyzer_cls.return_value = mock_analyzer
        
        # Act
        run_analysis_workflow(zipped_dir=str(tmp_path))
        
        # Assert
        assert mock_analyzer.run_analysis_from_path.call_count == 2