from unittest.mock import patch, MagicMock
from pathlib import Path
from utils.zip_repos import (
    zip_repos,
    validate_cloned_directory,
    find_repos,
    zip_all_repos,
    print_summary
)


class TestValidateClonedDirectory:
    def test_returns_true_when_directory_exists(self, tmp_path):
        assert validate_cloned_directory(tmp_path, "cloned_repos") is True

    def test_returns_false_when_directory_missing(self, tmp_path, capsys):
        fake_path = tmp_path / "nonexistent"
        result = validate_cloned_directory(fake_path, "cloned_repos")
        assert result is False
        out = capsys.readouterr().out
        assert "does not exist" in out


class TestFindRepos:
    def test_finds_repos_with_git_folder(self, tmp_path):
        # Create: cloned_repos/label1/repo1/.git
        label_dir = tmp_path / "label1"
        label_dir.mkdir()
        repo_dir = label_dir / "repo1"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        repos = find_repos(tmp_path)
        assert len(repos) == 1
        assert repos[0].name == "repo1"

    def test_ignores_directories_without_git(self, tmp_path):
        label_dir = tmp_path / "label1"
        label_dir.mkdir()
        repo_dir = label_dir / "not_a_repo"
        repo_dir.mkdir()

        repos = find_repos(tmp_path)
        assert len(repos) == 0

    def test_finds_multiple_repos(self, tmp_path):
        for label in ["label1", "label2"]:
            label_dir = tmp_path / label
            label_dir.mkdir()
            repo_dir = label_dir / f"repo_{label}"
            repo_dir.mkdir()
            (repo_dir / ".git").mkdir()

        repos = find_repos(tmp_path)
        assert len(repos) == 2

    def test_ignores_files_in_cloned_path(self, tmp_path):
        (tmp_path / "readme.txt").touch()
        repos = find_repos(tmp_path)
        assert len(repos) == 0


class TestZipAllRepos:
    def test_zips_repos_successfully(self, tmp_path):
        # Setup repo
        repo_path = tmp_path / "repos" / "label" / "myrepo"
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()
        (repo_path / "file.py").touch()

        zipped_path = tmp_path / "zipped"
        zipped_path.mkdir()

        repo_paths = [repo_path]
        success, fail = zip_all_repos(repo_paths, zipped_path)

        assert success == 1
        assert fail == 0
        assert (zipped_path / "myrepo.zip").exists()

    def test_handles_zip_failure(self, tmp_path):
        repo_path = tmp_path / "repos" / "label" / "badrepo"
        repo_path.mkdir(parents=True)

        zipped_path = tmp_path / "zipped"
        zipped_path.mkdir()

        with patch("shutil.make_archive", side_effect=Exception("zip error")):
            success, fail = zip_all_repos([repo_path], zipped_path)

        assert success == 0
        assert fail == 1

    def test_returns_correct_counts_for_mixed_results(self, tmp_path):
        repo1 = tmp_path / "repos" / "label" / "repo1"
        repo2 = tmp_path / "repos" / "label" / "repo2"
        repo1.mkdir(parents=True)
        repo2.mkdir(parents=True)

        zipped_path = tmp_path / "zipped"
        zipped_path.mkdir()

        call_count = 0
        def mock_archive(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("fail")

        with patch("shutil.make_archive", side_effect=mock_archive):
            success, fail = zip_all_repos([repo1, repo2], zipped_path)

        assert success == 1
        assert fail == 1


class TestPrintSummary:
    def test_prints_success_count(self, capsys):
        print_summary(5, 0, "zipped_repos")
        out = capsys.readouterr().out
        assert "Zipped: 5" in out
        assert "Failed" not in out

    def test_prints_failure_count_when_nonzero(self, capsys):
        print_summary(3, 2, "zipped_repos")
        out = capsys.readouterr().out
        assert "Zipped: 3" in out
        assert "Failed: 2" in out

    def test_prints_output_directory(self, capsys):
        print_summary(1, 0, "my_zips")
        out = capsys.readouterr().out
        assert "my_zips" in out


class TestZipRepos:
    def test_exits_early_if_cloned_dir_missing(self, tmp_path, capsys):
        with patch("utils.zip_repos.Path") as mock_path:
            mock_cloned = MagicMock()
            mock_cloned.exists.return_value = False
            mock_path.return_value = mock_cloned

            zip_repos("nonexistent", "zipped")

        out = capsys.readouterr().out
        assert "does not exist" in out

    def test_exits_early_if_no_repos_found(self, tmp_path, capsys):
        cloned = tmp_path / "cloned"
        cloned.mkdir()

        zip_repos(str(cloned), str(tmp_path / "zipped"))

        out = capsys.readouterr().out
        assert "No repositories found" in out

    def test_full_workflow(self, tmp_path, capsys):
        # Setup directory structure
        cloned = tmp_path / "cloned"
        zipped = tmp_path / "zipped"
        label_dir = cloned / "label1"
        repo_dir = label_dir / "test_repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / ".git").mkdir()
        (repo_dir / "main.py").write_text("print('hello')")

        zip_repos(str(cloned), str(zipped))

        out = capsys.readouterr().out
        assert "Found 1 repositories" in out
        assert "Zipped: 1" in out
        assert (zipped / "test_repo.zip").exists()