from datetime import datetime
from unittest.mock import patch, MagicMock
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.analyzers.contribution_analyzer import ContributionStats
from src.managers.ConfigManager import ConfigManager
from src.managers.ProjectManager import ProjectManager
from src.managers.FileHashManager import FileHashManager
from src.models.Project import Project
from src.models.ReportProject import PortfolioDetails
from src.ZipParser import parse_zip_to_project_folders
from src.ProjectFolder import ProjectFolder
from pathlib import Path
import pytest
import zipfile

# Fixtures
@pytest.fixture
def mock_config_manager():
    return MagicMock(spec=ConfigManager)

@pytest.fixture
def analyzer(mock_config_manager):
    dummy_zip = Path("/dummy/path.zip")
    # Start with empty root_folders, as they are loaded by load_zip
    return ProjectAnalyzer(
        config_manager=mock_config_manager,
        root_folders=[],
        zip_path=dummy_zip
    )

def test_load_zip_success(tmp_path):
    """Test that a successful parse returns the correct ProjectFolder objects."""
    # Create a real, temporary zip file for the test
    zip_location = tmp_path / "fake.zip"
    with zipfile.ZipFile(zip_location, 'w') as zf:
        zf.writestr("project-a/file.txt", "content")

    # Mock user input to provide the path to our real temp zip
    with patch("builtins.input", return_value=str(zip_location)):
        root_folders, _ = ProjectAnalyzer.load_zip()

    assert len(root_folders) == 1
    assert isinstance(root_folders[0], ProjectFolder)
    assert root_folders[0].name == 'project-a'

def test_load_zip_retry_then_success(tmp_path):
    """Test that the load function retries and then succeeds with a real file."""
    # Create the valid zip file
    good_zip_location = tmp_path / "good.zip"
    with zipfile.ZipFile(good_zip_location, 'w') as zf:
        zf.writestr("project-b/file.txt", "content")

    # Simulate user typing a bad path, then the good one
    inputs = iter(["/tmp/bad.zip", str(good_zip_location)])

    with patch("builtins.input", side_effect=inputs):
        root_folders, _ = ProjectAnalyzer.load_zip()

    assert len(root_folders) == 1
    assert isinstance(root_folders[0], ProjectFolder)
    assert root_folders[0].name == 'project-b'

def test_change_selected_users_workflow(analyzer, mock_config_manager):
    """Test the full workflow for changing selected users."""
    with patch.object(analyzer, '_get_projects', return_value=[Project(name="repo1", file_path="/fake/repo1")]), \
         patch("pathlib.Path.exists", return_value=True), \
         patch.object(analyzer.contribution_analyzer, 'get_all_authors', return_value={"alice@example.com": "Alice", "bob@example.com": "Bob"}), \
         patch.object(analyzer, '_prompt_for_usernames', return_value=["bob@example.com"]) as mock_prompt:

        analyzer.change_selected_users()

def test_initialize_projects_skips_older_zip_update(tmp_path, mock_config_manager):
    # Create a real file on disk so _has_project_changed can walk it
    project_dir = tmp_path / "project-a"
    project_dir.mkdir()
    (project_dir / "file.txt").write_text("original content")

    zip_location = tmp_path / "older.zip"
    with zipfile.ZipFile(zip_location, 'w') as zf:
        zf.writestr("project-a/file.txt", "original content")

    root_folders = parse_zip_to_project_folders(str(zip_location))
    analyzer = ProjectAnalyzer(mock_config_manager, root_folders, zip_location)
    analyzer.project_manager = ProjectManager(db_path=str(tmp_path / "projects.db"))
    analyzer.file_hash_manager = FileHashManager(db_path=str(tmp_path / "files.db"))

    existing = Project(
        name="project-a",
        file_path="/old/path",
        root_folder="project-a",
        last_modified=datetime(2024, 1, 1),
    )
    analyzer.project_manager.set(existing)

    # Pre-register the file hashes so it looks already seen
    analyzer._register_project_files(Project(name="project-a", file_path=str(project_dir)))

    with patch.object(analyzer, "ensure_cached_dir", return_value=tmp_path), \
         patch("src.analyzers.ProjectAnalyzer.RepoProjectBuilder.scan", return_value=[
             Project(name="project-a", file_path=str(project_dir), root_folder="project-a")
         ]):
        analyzer.initialize_projects()

    updated = analyzer.project_manager.get_by_name("project-a")
    assert updated.file_path == "/old/path"
    assert updated.last_modified == datetime(2024, 1, 1)


def test_initialize_projects_updates_newer_zip(tmp_path, mock_config_manager):
    # Create a real file on disk with NEW content that hasn't been hashed before
    project_dir = tmp_path / "project-b"
    project_dir.mkdir()
    (project_dir / "file.txt").write_text("brand new content")

    zip_location = tmp_path / "newer.zip"
    with zipfile.ZipFile(zip_location, 'w') as zf:
        zf.writestr("project-b/file.txt", "brand new content")

    root_folders = parse_zip_to_project_folders(str(zip_location))
    analyzer = ProjectAnalyzer(mock_config_manager, root_folders, zip_location)
    analyzer.project_manager = ProjectManager(db_path=str(tmp_path / "projects.db"))
    analyzer.file_hash_manager = FileHashManager(db_path=str(tmp_path / "files.db"))

    existing = Project(
        name="project-b",
        file_path="/old/path",
        root_folder="project-b",
        last_modified=datetime(2023, 1, 1),
    )
    analyzer.project_manager.set(existing)

    # Do NOT pre-register hashes — simulates new/changed files

    with patch.object(analyzer, "ensure_cached_dir", return_value=tmp_path), \
         patch("src.analyzers.ProjectAnalyzer.RepoProjectBuilder.scan", return_value=[
             Project(name="project-b", file_path=str(project_dir), root_folder="project-b")
         ]):
        analyzer.initialize_projects()

    updated = analyzer.project_manager.get_by_name("project-b")
    assert updated.file_path == str(project_dir)


def test_initialize_projects_does_not_duplicate_projects(tmp_path, mock_config_manager):
    zip_location = tmp_path / "same.zip"
    with zipfile.ZipFile(zip_location, 'w') as zf:
        zf.writestr("project-c/file.txt", "content")

    root_folders = parse_zip_to_project_folders(str(zip_location))
    analyzer = ProjectAnalyzer(mock_config_manager, root_folders, zip_location)
    analyzer.project_manager = ProjectManager(db_path=str(tmp_path / "projects.db"))
    analyzer.file_hash_manager = FileHashManager(db_path=str(tmp_path / "files.db"))

    with patch.object(analyzer, "ensure_cached_dir", return_value=tmp_path), \
         patch("src.analyzers.ProjectAnalyzer.RepoProjectBuilder.scan", return_value=[
             Project(name="project-c", file_path="/path", root_folder="project-c")
         ]), \
         patch.object(analyzer, "_has_project_changed", return_value=False):
        analyzer.initialize_projects()
        analyzer.initialize_projects()

    projects = list(analyzer.project_manager.get_all())
    assert len(projects) == 1

def test_register_project_files_dedupes_across_uploads(tmp_path, mock_config_manager):
    project_a_dir = tmp_path / "project-a"
    project_b_dir = tmp_path / "project-b"
    project_a_dir.mkdir()
    project_b_dir.mkdir()

    content = "same file contents"
    (project_a_dir / "file.txt").write_text(content)
    (project_b_dir / "file.txt").write_text(content)

    analyzer = ProjectAnalyzer(mock_config_manager, [], tmp_path / "dummy.zip")
    analyzer.file_hash_manager = FileHashManager(db_path=str(tmp_path / "files.db"))

    proj_a = Project(name="project-a", file_path=str(project_a_dir))
    proj_b = Project(name="project-b", file_path=str(project_b_dir))

    result_a = analyzer._register_project_files(proj_a)
    result_b = analyzer._register_project_files(proj_b)

    assert result_a["new"] == 1
    assert result_a["duplicate"] == 0
    assert result_b["new"] == 0
    assert result_b["duplicate"] == 1

    all_hashes = list(analyzer.file_hash_manager.get_all())
    assert len(all_hashes) == 1

def test_edit_skills(analyzer, monkeypatch):
    p1 = Project()
    p1.name='p1'
    p1.skills_used=['Skill1','Skill2','Skill3']
    p1.skills_selected=[] #start empty so we can check that it auto-fills

    items = [p1]

    #Exit without selecting project
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['x']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['x']):
            assert analyzer.edit_skills() == -1
    
    #check empty list auto fills
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['1','s','x']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['1','s','x']):
            assert analyzer.edit_skills() == True
            assert p1.skills_used == p1.skills_selected

    #p1 now selecting Skill1,Skill2,Skill3

    #remove Skill2
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['1','2','s','x']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['1','2','s','x']):
            assert analyzer.edit_skills() == True
            assert 'Skill2' not in p1.skills_selected
    
    #p1 now selecting Skill1,Skill3

    #remove Skill3, re-enable skill 2
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['1','3','2','s','x']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['1','3','2','s','x']):
            assert analyzer.edit_skills() == True
            assert 'Skill3' not in p1.skills_selected
            assert 'Skill2' in p1.skills_selected
    
    #p1 now selecting Skill1,Skill2

    #remove Skill1, enable all skills
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['1','1','a','s','x']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['1','1','a','s','x']):
            assert analyzer.edit_skills() == True
            assert 'Skill1' in p1.skills_selected
            assert 'Skill3' in p1.skills_selected
            assert 'Skill2' in p1.skills_selected

    #Incorrect project selection, incorrect skill selection, exit without saving
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['9','1','9','x']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['9','1','9','x']):
            assert analyzer.edit_skills() == False #False if not saved

def test_update_score_and_date(analyzer, monkeypatch):

    date1='2001-01-01'
    date2='2002-02-02'
    date3='2003-03-03'
    date4='2004-04-04'

    p1 = Project()
    p1.name='p1'
    p1.resume_score=5.0
    p1.date_created=datetime.strptime(date1,'%Y-%m-%d').date()
    p1.last_modified=datetime.strptime(date2,'%Y-%m-%d').date()

    #version of p1 that has the intended final state for comparsion
    p1_final = Project()
    p1_final.name='p1'
    p1_final.resume_score=20.0
    p1_final.date_created=datetime.strptime(date3,'%Y-%m-%d').date()
    p1_final.last_modified=datetime.strptime(date4,'%Y-%m-%d').date()

    items =  []
    items.append(p1)

    #Start function
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['oops', 'g score 10.0', '01 scobe 20.0', '01 created thisisadate', '01 modified 2004-04-04','s','x']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['oops', 'g score 10.0', '01 scobe 20.0', '01 created thisisadate', '01 modified 2004-04-04','s','x']):
            analyzer.update_score_and_date()
            assert p1.last_modified == p1_final.last_modified
    #What this tests:
        #1) incorrect command length
        #2) incorrect index
        #3) incorrect command name
        #4) invalid score
        #5) invalid date
        #6) valid last modified [2004-04-04]
        #7) save
        #8) exit

    #Start function
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['01 created 2003-03-03','s','x']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['01 created 2003-03-03','s','x']):
            analyzer.update_score_and_date()
            assert p1.date_created == p1_final.date_created
    #What this tests:
        #1) valid last created [2003-03-03]
        #2) save
        #3) exit
    
    #Start function
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['01 created 2003-03-03','s','x']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['01 score 20.0','s','x']):
            analyzer.update_score_and_date()
            assert p1.date_created == p1_final.date_created
    #What this tests:
        #1) valid score 20.0
        #2) save
        #3) exit
        
def test_delete_previous_insights_clears_portfolio_details(analyzer):
    project = Project(name="demo", file_path="/tmp/demo")
    project.portfolio_details = PortfolioDetails(project_name="demo")
    analyzer.project_manager = MagicMock()
    analyzer.project_manager.get_all.return_value = [project]

    with patch.object(analyzer, "_select_project", return_value=project):
        analyzer.delete_previous_insights()

    assert project.portfolio_details.project_name == ""

def test_resolve_selected_authors_matches_case_insensitively(analyzer):
    resolved = analyzer._resolve_selected_authors(
        requested_authors=["alice", "BOB", "missing"],
        available_authors=["Alice", "Bob"],
    )

    assert resolved == ["Alice", "Bob"]


def test_analyze_git_and_contributions_non_interactive_uses_configured_usernames(analyzer, mock_config_manager):
    project = Project(name="repo1", file_path="/fake/repo1")
    analyzer.project_manager = MagicMock()
    mock_config_manager.get.return_value = ["alice@example.com"]

    fake_stats = {
        "alice@example.com": ContributionStats(lines_added=10, lines_deleted=0, total_commits=1),
        "bob@example.com": ContributionStats(lines_added=10, lines_deleted=0, total_commits=1),
    }

    with patch("pathlib.Path.exists", return_value=True), \
         patch.object(analyzer.contribution_analyzer, "get_all_authors", return_value={"alice@example.com": "Alice", "bob@example.com": "Bob"}), \
         patch.object(analyzer.contribution_analyzer, "detect_and_write_mailmap", side_effect=lambda repo, m, config_manager=None: m), \
         patch.object(analyzer.contribution_analyzer, "analyze", return_value=fake_stats):
        analyzer.analyze_git_and_contributions(projects=[project], interactive=False)

    assert project.authors == ["Alice"]
    assert project.individual_contributions["contribution_share_percent"] == 50.0

def test_compare_projects(analyzer, monkeypatch):
    p1 = Project()
    p1.name='p1'
    p1.size_kb = 1
    p1.num_files =1
    p1.author_count=1
    p1.languages = ['1']
    p1.frameworks = ['1']
    p1.skills_used = ['1']
    p1.dependencies_list = ['1']
    p1.total_loc = 1
    p1.comment_ratio = 1
    p1.test_file_ratio = 1
    p1.avg_functions_per_file = 1
    p1.testing_discipline_score = 1
    p1.documentation_habits_score = 1
    p1.modularity_score = 1
    p1.language_depth_score = 1
    p1.resume_score = 1
    p1.date_created = datetime.strptime('1111-01-01','%Y-%m-%d').date()
    p1.last_modified = datetime.strptime('1111-01-01','%Y-%m-%d').date()

    p2 = Project()
    p2.name='p2'
    p2.size_kb = 2
    p2.num_files = 2
    p2.author_count=2
    p2.languages = ['1','2']
    p2.frameworks = ['1','2']
    p2.skills_used = ['1','2']
    p2.dependencies_list = ['1','2']
    p2.total_loc = 2
    p2.comment_ratio = 2
    p2.test_file_ratio = 2
    p2.avg_functions_per_file = 2
    p2.testing_discipline_score = 2
    p2.documentation_habits_score = 2
    p2.modularity_score = 2
    p2.language_depth_score = 2
    p2.resume_score = 2
    p2.date_created = datetime.strptime('2222-02-02','%Y-%m-%d').date()
    p2.last_modified = datetime.strptime('2222-02-02','%Y-%m-%d').date()

    items =  [p1, p2]

    expected = [p2, p1] #every sort method should result in this order

    #[0]  incorrect input
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['oops','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['oops','flush']):
            result = analyzer.compare_projects()
            assert items == result #unchanged output
    #[1]  Size of project (kb)
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['1','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['1','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[2]  # of files
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['2','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['2','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[3]  # of Authors
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['3','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['3','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[4]  # of languages
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['4','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['4','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[5]  # of frameworks
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['5','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['5','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[6]  # of skills
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['6','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['6','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[7]  # of dependencies
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['7','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['7','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[8]  # of lines of code
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['8','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['8','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[9]  Comments/lines of code
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['9','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['9','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[10] Test file/code file
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['10','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['10','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[11] Average functions/code file
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['11','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['11','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[12] Testing Discipline Score
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['12','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['12','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[13] Documentation Habits Score
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['13','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['13','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[14] Modularity Score
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['14','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['14','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[15] Language Depth Score
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['15','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['15','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[16] Resume Score
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['16','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['16','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[17] Date Created
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['17','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['17','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[18] Last Modified
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['18','flush']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['18','flush']):
            result = analyzer.compare_projects()
            assert expected == result
    #[x]  Exit
    with patch.object(analyzer, '_get_projects', return_value=items):
        inputs = ['x']
        monkeypatch.setattr('builtins.input', lambda prompt: inputs.pop(0))
        with patch('builtins.input', side_effect=['x']):
            result = analyzer.compare_projects()
            assert result == -1
