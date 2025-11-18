from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from utils.wipe_repos import (run_wipe_workflow,wipe_repos,clean_up_directories)

class TestRunWipeWorkflow:
    def test_cloned_repos_dir_does_not_exist(self):
        with patch('pathlib.Path.exists', return_value=False), \
             patch('builtins.print') as mock_print:
            run_wipe_workflow()
            mock_print.assert_called_once_with("Nothing to wipe - cloned_repos/ doesn't exist")
    
    def test_csv_not_found(self):
        with patch('pathlib.Path.exists') as mock_exists, \
             patch('builtins.print') as mock_print:
            mock_exists.side_effect = [True, False]
            run_wipe_workflow('missing.csv')
            mock_print.assert_called_with("CSV not found: missing.csv")
    
    def test_successful_workflow(self):
        csv_content = """repo_name,repo_label,repo_link 
        test-repo,backend,https://github.com/test/repo.git 
        another-repo,frontend,https://github.com/test/another.git"""
        with patch('pathlib.Path.exists') as mock_exists, \
             patch('builtins.open', mock_open(read_data=csv_content)), \
             patch('utils.wipe_repos.wipe_repos', return_value=(2, 0)) as mock_wipe, \
             patch('utils.wipe_repos.clean_up_directories') as mock_cleanup, \
             patch('utils.wipe_repos.print_summary') as mock_summary, \
             patch('builtins.print'):
            mock_exists.side_effect = [True, True, True, True]
            run_wipe_workflow()
            assert mock_wipe.call_count == 1
            repos_arg = mock_wipe.call_args[0][0]
            assert len(repos_arg) == 2
            mock_cleanup.assert_called_once()
            mock_summary.assert_called_once_with(2, 0)

class TestWipeRepos:
    def test_successful_delete_multiple_repos(self):
        """Test successfully deleting multiple repositories."""
        repos = [
            {'repo_name': 'repo1', 'repo_label': 'backend', 'repo_link': 'https://github.com/test/repo1.git'},
            {'repo_name': 'repo2', 'repo_label': 'frontend', 'repo_link': 'https://github.com/test/repo2.git'},
            {'repo_name': 'repo3', 'repo_label': 'mobile', 'repo_link': 'https://github.com/test/repo3.git'},]
        cloned_repos_dir = Path('cloned_repos')
        with patch('shutil.rmtree') as mock_rmtree, \
             patch('builtins.print'):
            deleted, failed = wipe_repos(repos, cloned_repos_dir)
            assert deleted == 3
            assert failed == 0
            assert mock_rmtree.call_count == 3
    
    def test_failed_delete(self):
        repos = [{'repo_name': 'locked-repo', 'repo_label': 'backend', 'repo_link': 'https://github.com/test/repo.git'}]
        cloned_repos_dir = Path('cloned_repos')
        with patch('shutil.rmtree', side_effect=PermissionError("Access denied")), \
             patch('builtins.print') as mock_print:
            deleted, failed = wipe_repos(repos, cloned_repos_dir)
            assert deleted == 0
            assert failed == 1
            assert any("Failed to delete" in str(call) for call in mock_print.call_args_list)

class TestCleanUpDirectories:
    def test_cleanup_empty_label_directories(self):
        cloned_repos_dir = Path('cloned_repos')
        mock_backend = Mock(spec=Path)
        mock_backend.is_dir.return_value = True
        mock_backend.iterdir.return_value = []
        mock_backend.name = 'backend'
        mock_frontend = Mock(spec=Path)
        mock_frontend.is_dir.return_value = True
        mock_frontend.iterdir.return_value = [Mock()]
        mock_frontend.name = 'frontend'
        with patch.object(Path, 'iterdir', return_value=[mock_backend, mock_frontend]), \
             patch('builtins.print'):
            clean_up_directories(cloned_repos_dir)
            mock_backend.rmdir.assert_called_once()
            mock_frontend.rmdir.assert_not_called()

class TestIntegration:
    def test_full_wipe_workflow_integration(self):
        csv_content = """repo_name,repo_label,repo_link
    test-repo,backend,https://github.com/test/repo.git
    another-repo,frontend,https://github.com/test/another.git"""
        with patch('pathlib.Path.exists') as mock_exists, \
            patch('builtins.open', mock_open(read_data=csv_content)), \
            patch('shutil.rmtree') as mock_rmtree, \
            patch('pathlib.Path.iterdir', return_value=[]), \
            patch('pathlib.Path.rmdir'), \
            patch('builtins.print'):
            mock_exists.side_effect = [True, True, True, True]
            run_wipe_workflow('test.csv')
            assert mock_rmtree.call_count == 2
