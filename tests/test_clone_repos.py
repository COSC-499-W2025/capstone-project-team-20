import subprocess
from pathlib import Path
from unittest.mock import patch, mock_open
from utils.clone_repos import (
    ensure_gitignore,
    run_clone_workflow,
    clone_repos,
    print_summary
)


class TestEnsureGitignore:
    """Tests for ensure_gitignore function."""
    
    def test_gitignore_exists_without_cloned_repos(self):
        """Test adding cloned_repos/ when .gitignore exists but doesn't contain it."""
        mock_content = "*.pyc\n__pycache__/\n"
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=mock_content), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('builtins.print') as mock_print:
            result = ensure_gitignore()
            assert result is True
            mock_file.assert_called_once_with(Path('.gitignore'), 'a')
            mock_file().write.assert_called_once_with('\ncloned_repos/\n')
            mock_print.assert_called_once_with("Added cloned_repos/ to .gitignore")
    
    def test_gitignore_missing(self):
        """Test when .gitignore doesn't exist."""
        with patch('pathlib.Path.exists', return_value=False), \
             patch('builtins.print') as mock_print:
            result = ensure_gitignore()
            assert result is False
            mock_print.assert_called_once_with("Error: .gitignore seems to be missing")


class TestRunCloneWorkflow:
    """Tests for run_clone_workflow function."""
    
    def test_successful_workflow(self):
        """Test complete workflow with valid CSV."""
        mock_csv_data = [
            {'repo_name': 'test-repo', 'repo_label': 'backend', 'repo_link': 'https://github.com/test/repo.git'}
        ]
        
        with patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('utils.clone_repos.ensure_gitignore', return_value=True), \
             patch('builtins.open', mock_open(read_data='repo_name,repo_label,repo_link\n')), \
             patch('csv.DictReader', return_value=mock_csv_data), \
             patch('utils.clone_repos.clone_repos', return_value=(1, 0, 0)), \
             patch('utils.clone_repos.print_summary') as mock_summary, \
             patch('builtins.print'):
            run_clone_workflow()
            mock_summary.assert_called_once_with(1, 0, 0)
    
    def test_csv_not_found(self):
        """Test when CSV file doesn't exist."""
        with patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=False), \
             patch('utils.clone_repos.ensure_gitignore', return_value=True), \
             patch('builtins.print') as mock_print:
            run_clone_workflow('missing.csv')
            mock_print.assert_any_call("CSV not found: missing.csv")


class TestCloneRepos:
    """Tests for clone_repos function."""
    
    def test_successful_clone(self):
        """Test successful cloning of a repository."""
        repos = [
            {'repo_name': 'test-repo', 'repo_label': 'backend', 'repo_link': 'https://github.com/test/repo.git'}
        ]
        cloned_repos_dir = Path('cloned_repos')
        
        with patch('pathlib.Path.exists', return_value=False), \
             patch('pathlib.Path.mkdir'), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.print'):
            success, skip, fail = clone_repos(repos, cloned_repos_dir)
            assert success == 1
            assert skip == 0
            assert fail == 0
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[:4] == ['git', 'clone', '--depth', '1']
    
    def test_skip_existing_repo(self):
        """Test skipping a repository that already exists."""
        repos = [
            {'repo_name': 'existing-repo', 'repo_label': 'backend', 'repo_link': 'https://github.com/test/repo.git'}
        ]
        cloned_repos_dir = Path('cloned_repos')
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.print'):
            success, skip, fail = clone_repos(repos, cloned_repos_dir)
            assert success == 0
            assert skip == 1
            assert fail == 0
            mock_run.assert_not_called()

    def test_clone_subprocess_error(self):
        """Test handling of subprocess errors."""
        repos = [
            {'repo_name': 'bad-repo', 'repo_label': 'backend', 'repo_link': 'https://github.com/test/nonexistent.git'}
        ]
        cloned_repos_dir = Path('cloned_repos')
        
        error = subprocess.CalledProcessError(1, 'git', stderr='fatal: repository not found')
        
        with patch('pathlib.Path.exists', return_value=False), \
             patch('pathlib.Path.mkdir'), \
             patch('subprocess.run', side_effect=error), \
             patch('builtins.print'):
            success, skip, fail = clone_repos(repos, cloned_repos_dir)
            assert success == 0
            assert skip == 0
            assert fail == 1

    
    def test_multiple_repos_mixed_results(self):
        """Test cloning multiple repositories with mixed results."""
        repos = [
            {'repo_name': 'repo1', 'repo_label': 'backend', 'repo_link': 'https://github.com/test/repo1.git'},
            {'repo_name': 'repo2', 'repo_label': 'frontend', 'repo_link': 'https://github.com/test/repo2.git'},
            {'repo_name': 'repo3', 'repo_label': 'backend', 'repo_link': 'https://github.com/test/repo3.git'},
        ]
        cloned_repos_dir = Path('cloned_repos')

        def mock_exists(self):
            return str(self).endswith('repo2')
        
        def mock_run(*args, **kwargs):
            if 'repo3' in args[0][-1]:
                raise subprocess.CalledProcessError(1, 'git', stderr='error')
        
        with patch('pathlib.Path.exists', mock_exists), \
             patch('pathlib.Path.mkdir'), \
             patch('subprocess.run', side_effect=mock_run), \
             patch('builtins.print'):
            success, skip, fail = clone_repos(repos, cloned_repos_dir)
            assert success == 1
            assert skip == 1
            assert fail == 1


class TestIntegration:
    """Integration tests for the entire workflow."""
    
    def test_full_workflow_integration(self):
        """Test the complete workflow from CSV to cloning."""
        csv_content = """repo_name,repo_label,repo_link
test-repo,backend,https://github.com/test/repo.git
another-repo,frontend,https://github.com/test/another.git"""
        
        with patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.read_text', return_value=''), \
             patch('builtins.open', mock_open(read_data=csv_content)), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.print'):
            mock_exists.side_effect = [True, True, False, False]
            run_clone_workflow('test.csv')
            assert mock_run.call_count == 2
