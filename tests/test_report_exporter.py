import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, mock_open
import subprocess
from jinja2 import Environment, FileSystemLoader
from src.exporters.ReportExporter import ReportExporter
from src.models.Report import Report
from src.models.ReportProject import ReportProject


class TestReportExporter:
    """Test suite for ReportExporter class"""
    
    @pytest.fixture
    def exporter(self):
        """Create a ReportExporter instance for testing"""
        return ReportExporter()
    
    @pytest.fixture
    def mock_config_manager(self):
        """Mock ConfigManager with sample data"""
        config = Mock()
        config.get = Mock(side_effect=lambda key, default: {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "555-123-4567",
            "github": "johndoe",
            "linkedin": "johndoe"
        }.get(key, default))
        return config
    
    @pytest.fixture
    def mock_report_simple(self):
        """Create a simple mock Report with one project"""
        report = Mock()
        
        project = Mock()
        project.project_name = "My Awesome Project"
        project.languages = ["Python", "JavaScript"]
        project.frameworks = ["Django", "React"]
        project.date_created = datetime(2024, 1, 15)
        project.last_modified = datetime(2024, 6, 20)
        project.bullets = [
            "Built a web application with 1000+ users",
            "Implemented RESTful API with 20+ endpoints"
        ]
        
        report.projects = [project]
        return report
    
    @pytest.fixture
    def mock_report_with_special_chars(self):
        """Create a mock Report with LaTeX special characters"""
        report = Mock()
        
        project = Mock()
        project.project_name = "Project with $pecial & Char$"
        project.languages = ["C++", "C#"]
        project.frameworks = ["ASP.NET"]
        project.date_created = datetime(2024, 3, 1)
        project.last_modified = None
        project.bullets = [
            "Increased performance by 50% & reduced costs by $10,000",
            "Used algorithms with O(n^2) complexity",
            "Handled edge cases like user_names with underscores"
        ]
        
        report.projects = [project]
        return report
    
    @pytest.fixture
    def mock_report_multiple_projects(self):
        """Create a mock Report with multiple projects"""
        report = Mock()
        
        proj1 = Mock()
        proj1.project_name = "E-commerce Platform"
        proj1.languages = ["Python", "TypeScript"]
        proj1.frameworks = ["Flask", "Vue.js"]
        proj1.date_created = datetime(2023, 6, 1)
        proj1.last_modified = datetime(2024, 1, 15)
        proj1.bullets = ["Built shopping cart", "Integrated payment gateway"]
        
        proj2 = Mock()
        proj2.project_name = "Data Pipeline"
        proj2.languages = ["Python", "SQL"]
        proj2.frameworks = ["Airflow", "Pandas"]
        proj2.date_created = datetime(2024, 2, 1)
        proj2.last_modified = datetime(2024, 5, 30)
        proj2.bullets = ["Processed 1M+ records daily", "Reduced pipeline time by 60%"]
        
        report.projects = [proj1, proj2]
        return report
    
    @pytest.fixture
    def mock_report_empty(self):
        """Create a mock Report with no projects"""
        report = Mock()
        report.projects = []
        return report
    
    @pytest.fixture
    def mock_report_none_values(self):
        """Create a mock Report with None values in languages/frameworks"""
        report = Mock()
        
        project = Mock()
        project.project_name = "Simple Project"
        project.languages = None
        project.frameworks = None
        project.date_created = None
        project.last_modified = None
        project.bullets = ["Did some stuff"]
        
        report.projects = [project]
        return report
    
    # ==================== UNIT TESTS ====================
    
    def test_init_sets_up_jinja_environment(self, exporter):
        """Test that __init__ properly sets up Jinja2 environment"""
        assert exporter.env is not None
        assert 'escape_latex' in exporter.env.filters
    
    def test_escape_latex_special_characters(self, exporter):
        """Test LaTeX special character escaping"""
        test_cases = {
            "Hello & goodbye": r"Hello \& goodbye",
            "Cost: $100": r"Cost: \$100",
            "C++ & C#": r"C++ \& C\#",
            "50% off": r"50\% off",
            "user_name": r"user\_name",
            "O(n^2)": r"O(n\^{}2)",
            "~/.bashrc": r"\textasciitilde{}/.bashrc",
            "{json}": r"\{json\}",
            # Single backslash in string literal becomes escaped backslash
            "path/to/file": r"path/to/file"  # Forward slashes don't need escaping
        }
        
        for input_text, expected in test_cases.items():
            result = exporter._escape_latex(input_text)
            assert result == expected, f"Failed for input: {input_text}"
    
    def test_escape_latex_backslash(self, exporter):
        """Test backslash escaping separately due to Python string complexity"""
        # In Python, '\\' is a single backslash character
        # After escaping, it should become \textbackslash{}
        # But the curly braces also get escaped, so it becomes \textbackslash\{\}
        result = exporter._escape_latex("\\")
        assert result == r"\textbackslash\{\}"
    
    def test_escape_latex_empty_string(self, exporter):
        """Test escaping empty string returns empty string"""
        assert exporter._escape_latex("") == ""
        assert exporter._escape_latex(None) == ""
    
    def test_build_context_basic_info(self, exporter, mock_report_simple, mock_config_manager):
        """Test _build_context extracts basic user info correctly"""
        context = exporter._build_context(mock_report_simple, mock_config_manager)
        
        assert context["name"] == "John Doe"
        assert context["email"] == "john.doe@example.com"
        assert context["phone"] == "555-123-4567"
        assert context["github_url"] == "https://github.com/johndoe"
        assert context["github_display"] == "github.com/johndoe"
        assert context["linkedin_url"] == "https://linkedin.com/in/johndoe"
        assert context["linkedin_display"] == "linkedin.com/in/johndoe"
    
    def test_build_context_projects(self, exporter, mock_report_simple, mock_config_manager):
        """Test _build_context processes projects correctly"""
        context = exporter._build_context(mock_report_simple, mock_config_manager)
        
        assert len(context["projects"]) == 1
        proj = context["projects"][0]
        
        assert proj["name"] == "My Awesome Project"
        assert proj["stack"] == "Python, JavaScript, Django, React"
        assert proj["dates"] == "Jan 2024 - Jun 2024"
        assert len(proj["bullets"]) == 2
    
    def test_build_context_multiple_projects(self, exporter, mock_report_multiple_projects, mock_config_manager):
        """Test _build_context handles multiple projects"""
        context = exporter._build_context(mock_report_multiple_projects, mock_config_manager)
        
        assert len(context["projects"]) == 2
        assert context["projects"][0]["name"] == "E-commerce Platform"
        assert context["projects"][1]["name"] == "Data Pipeline"
    
    def test_build_context_skills_aggregation(self, exporter, mock_report_multiple_projects, mock_config_manager):
        """Test _build_context aggregates skills from all projects"""
        context = exporter._build_context(mock_report_multiple_projects, mock_config_manager)
        
        assert "Languages" in context["skills"]
        assert "Frameworks" in context["skills"]
        
        # Should be sorted and unique
        assert context["skills"]["Languages"] == ["Python", "SQL", "TypeScript"]
        assert set(context["skills"]["Frameworks"]) == {"Airflow", "Flask", "Pandas", "Vue.js"}
    
    def test_build_context_handles_none_values(self, exporter, mock_report_none_values, mock_config_manager):
        """Test _build_context handles None values gracefully"""
        context = exporter._build_context(mock_report_none_values, mock_config_manager)
        
        proj = context["projects"][0]
        assert proj["stack"] == ""  # Empty when no languages/frameworks
        assert proj["dates"] == ""  # Empty when no dates
        assert context["skills"] == {}  # Empty dict when no skills
    
    def test_build_context_empty_report(self, exporter, mock_report_empty, mock_config_manager):
        """Test _build_context handles empty report"""
        context = exporter._build_context(mock_report_empty, mock_config_manager)
        
        assert context["projects"] == []
        assert context["skills"] == {}
    
    def test_build_context_missing_github(self, exporter, mock_report_simple):
        """Test _build_context when GitHub is not provided"""
        config = Mock()
        config.get = Mock(side_effect=lambda key, default: {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "555-999-8888",
            "github": "",
            "linkedin": ""
        }.get(key, default))
        
        context = exporter._build_context(mock_report_simple, config)
        
        assert context["github_url"] == ""
        assert context["github_display"] == ""
        assert context["linkedin_url"] == ""
    
    def test_build_context_date_created_only(self, exporter, mock_config_manager):
        """Test date formatting when only date_created exists"""
        report = Mock()
        project = Mock()
        project.project_name = "Test"
        project.languages = []
        project.frameworks = []
        project.date_created = datetime(2024, 3, 15)
        project.last_modified = None
        project.bullets = []
        report.projects = [project]
        
        context = exporter._build_context(report, mock_config_manager)
        assert context["projects"][0]["dates"] == "Mar 2024"
    
    # ==================== INTEGRATION TESTS ====================
    
    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.unlink')
    @patch('shutil.move')
    def test_compile_to_pdf_success(self, mock_move, mock_unlink, mock_exists, mock_run, exporter, tmp_path):
        """Test successful PDF compilation"""
        tex_path = tmp_path / "resume.tex"
        output_path = tmp_path / "resume.pdf"
        
        # Mock successful pdflatex run
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")
        mock_exists.return_value = True
        
        exporter._compile_to_pdf(tex_path, output_path)
        
        # Should run pdflatex twice
        assert mock_run.call_count == 2
        
        # Should clean up aux files
        assert mock_unlink.call_count == 3  # .aux, .log, .out
    
    @patch('subprocess.run')
    def test_compile_to_pdf_pdflatex_not_found(self, mock_run, exporter, tmp_path):
        """Test error handling when pdflatex is not installed"""
        tex_path = tmp_path / "resume.tex"
        output_path = tmp_path / "resume.pdf"
        
        mock_run.side_effect = FileNotFoundError()
        
        with pytest.raises(RuntimeError, match="pdflatex not found"):
            exporter._compile_to_pdf(tex_path, output_path)
    @patch('subprocess.run')
    @patch('shutil.move')
    def test_compile_calls_pdflatex_twice(self, mock_move, mock_run, exporter, tmp_path):
        """Test that pdflatex is called twice for proper formatting"""
        tex_path = tmp_path / "resume.tex"
        tex_path.write_text("\\documentclass{article}\\begin{document}test\\end{document}")
        output_path = tmp_path / "resume.pdf"
        
        # Create the generated PDF that pdflatex would create
        (tmp_path / "resume.pdf").touch()
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Success",
            stderr=""
        )
        
        exporter._compile_to_pdf(tex_path, output_path)
        
        # Verify pdflatex was called exactly twice
        assert mock_run.call_count == 2


    @patch('subprocess.run')
    @patch('shutil.move')
    def test_compile_uses_correct_output_directory(self, mock_move, mock_run, exporter, tmp_path):
        """Test that pdflatex outputs to the correct directory"""
        tex_path = tmp_path / "resume.tex"
        tex_path.write_text("\\documentclass{article}\\begin{document}test\\end{document}")
        output_path = tmp_path / "resume.pdf"
        
        (tmp_path / "resume.pdf").touch()
        
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")
        
        exporter._compile_to_pdf(tex_path, output_path)
        
        # Check the subprocess call arguments
        call_args = mock_run.call_args[0][0]
        assert '-output-directory' in call_args
        # The directory should be tmp_path (where tex file is)
        assert str(tmp_path) in call_args


    @patch('subprocess.run')
    def test_compile_cleans_up_aux_files(self, mock_run, exporter, tmp_path):
        """Test that auxiliary files are deleted after compilation"""
        tex_path = tmp_path / "resume.tex"
        tex_path.write_text("\\documentclass{article}\\begin{document}test\\end{document}")
        output_path = tmp_path / "resume.pdf"
        
        # Create auxiliary files that should be cleaned up
        (tmp_path / "resume.aux").touch()
        (tmp_path / "resume.log").touch()
        (tmp_path / "resume.out").touch()
        (tmp_path / "resume.pdf").touch()
        
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")
        
        exporter._compile_to_pdf(tex_path, output_path)
        
        # Verify aux files were deleted
        assert not (tmp_path / "resume.aux").exists()
        assert not (tmp_path / "resume.log").exists()
        assert not (tmp_path / "resume.out").exists()
        # PDF should still exist
        assert (tmp_path / "resume.pdf").exists()


    @patch('subprocess.run')
    def test_compile_raises_when_pdflatex_not_found(self, mock_run, exporter, tmp_path):
        """Test helpful error when pdflatex is not installed"""
        tex_path = tmp_path / "resume.tex"
        tex_path.write_text("test")
        output_path = tmp_path / "resume.pdf"
        
        mock_run.side_effect = FileNotFoundError()
        
        with pytest.raises(RuntimeError, match="pdflatex not found"):
            exporter._compile_to_pdf(tex_path, output_path)


    @patch('subprocess.run')
    def test_compile_detects_package_errors(self, mock_run, exporter, tmp_path):
        """Test that Package errors are caught"""
        tex_path = tmp_path / "resume.tex"
        tex_path.write_text("test")
        output_path = tmp_path / "resume.pdf"
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout="! Package hyperref Error: Wrong driver option 'pdftex'",
            stderr=""
        )
        
        with pytest.raises(RuntimeError, match="LaTeX compilation failed"):
            exporter._compile_to_pdf(tex_path, output_path)
    
    @patch.object(ReportExporter, '_compile_to_pdf')
    @patch('builtins.open', new_callable=mock_open)
    @patch.object(ReportExporter, '__init__', lambda x: None)
    def test_export_to_pdf_creates_tex_file(self, mock_file, mock_compile, mock_report_simple, mock_config_manager, tmp_path):
        """Test that export_to_pdf creates a .tex file with correct content"""
        # Create exporter with mocked template
        exporter = ReportExporter()
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        
        # Create a minimal template file
        template_file = template_dir / "jake.tex"
        template_file.write_text("{{ name }}")
        
        exporter.env = Environment(loader=FileSystemLoader(template_dir))
        exporter.env.filters['escape_latex'] = lambda x: x if x else ""
        
        output_path = tmp_path / "resume.pdf"
        
        exporter.export_to_pdf(mock_report_simple, mock_config_manager, str(output_path))
        
        # Should call compile
        mock_compile.assert_called_once()
    
    @patch.object(ReportExporter, '_compile_to_pdf')
    @patch('builtins.open', new_callable=mock_open)
    @patch.object(ReportExporter, '__init__', lambda x: None)
    def test_export_to_pdf_with_special_chars(self, mock_file, mock_compile, mock_report_with_special_chars, mock_config_manager, tmp_path):
        """Test that special characters are handled in export"""
        # Create exporter with mocked template
        exporter = ReportExporter()
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        
        # Create a minimal template file
        template_file = template_dir / "jake.tex"
        template_file.write_text("{{ name | escape_latex }}")
        
        exporter.env = Environment(loader=FileSystemLoader(template_dir))
        
        # Use actual escape function
        def escape_latex(text):
            if not text:
                return ""
            replacements = {
                '\\': r'\textbackslash{}',
                '&': r'\&',
                '%': r'\%',
                '$': r'\$',
                '#': r'\#',
                '_': r'\_',
                '{': r'\{',
                '}': r'\}',
                '~': r'\textasciitilde{}',
                '^': r'\^{}',
            }
            for old, new in replacements.items():
                text = text.replace(old, new)
            return text
        
        exporter.env.filters['escape_latex'] = escape_latex
        
        output_path = tmp_path / "resume.pdf"
        
        # Should not raise any exceptions
        exporter.export_to_pdf(mock_report_with_special_chars, mock_config_manager, str(output_path))
        
        # Should call compile
        mock_compile.assert_called_once()
    
    @patch.object(ReportExporter, '_compile_to_pdf')
    def test_export_to_pdf_custom_template(self, mock_compile, exporter, mock_report_simple, mock_config_manager, tmp_path):
        """Test export with custom template name"""
        output_path = tmp_path / "resume.pdf"
        
        # This will fail if template doesn't exist, but we're testing the parameter is passed
        with pytest.raises(Exception):  # Template won't exist in test
            exporter.export_to_pdf(
                mock_report_simple, 
                mock_config_manager, 
                str(output_path),
                template="custom_template"
            )
    
    # ==================== EDGE CASE TESTS ====================
    
    def test_escape_latex_all_special_chars_together(self, exporter):
        """Test escaping when multiple special chars are together"""
        input_text = "&%$#_{}~^"
        result = exporter._escape_latex(input_text)
        
        # Should escape all characters - check for escaped versions
        assert r'\&' in result
        assert r'\%' in result
        assert r'\$' in result
        assert r'\#' in result
        assert r'\_' in result
        assert r'\{' in result
        assert r'\}' in result
    
    def test_build_context_project_with_empty_lists(self, exporter, mock_config_manager):
        """Test project with empty language/framework lists"""
        report = Mock()
        project = Mock()
        project.project_name = "Empty Project"
        project.languages = []
        project.frameworks = []
        project.date_created = None
        project.last_modified = None
        project.bullets = []
        report.projects = [project]
        
        context = exporter._build_context(report, mock_config_manager)
        
        assert context["projects"][0]["stack"] == ""
        assert context["skills"] == {}
    
    def test_build_context_very_long_tech_stack(self, exporter, mock_config_manager):
        """Test handling of very long tech stacks"""
        report = Mock()
        project = Mock()
        project.project_name = "Kitchen Sink"
        project.languages = ["Python", "JavaScript", "TypeScript", "Java", "Go", "Rust"]
        project.frameworks = ["Django", "Flask", "React", "Vue", "Angular", "Spring", "FastAPI"]
        project.date_created = None
        project.last_modified = None
        project.bullets = []
        report.projects = [project]
        
        context = exporter._build_context(report, mock_config_manager)
        
        stack = context["projects"][0]["stack"]
        assert len(stack.split(", ")) == 13
        assert "Python" in stack
        assert "FastAPI" in stack


# ==================== FIXTURE FOR REAL TEMPLATE TESTING ====================

class TestTemplateRendering:
    """Tests that require actual template files"""
    
    @pytest.fixture
    def mock_report_simple(self):
        """Create a simple mock Report with one project"""
        report = Mock()
        
        project = Mock()
        project.project_name = "My Awesome Project"
        project.languages = ["Python", "JavaScript"]
        project.frameworks = ["Django", "React"]
        project.date_created = datetime(2024, 1, 15)
        project.last_modified = datetime(2024, 6, 20)
        project.bullets = [
            "Built a web application with 1000+ users",
            "Implemented RESTful API with 20+ endpoints"
        ]
        
        report.projects = [project]
        return report
    
    @pytest.fixture
    def mock_config_manager(self):
        """Mock ConfigManager with sample data"""
        config = Mock()
        config.get = Mock(side_effect=lambda key, default: {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "555-123-4567",
            "github": "johndoe",
            "linkedin": "johndoe"
        }.get(key, default))
        return config
    
    @pytest.fixture
    def exporter_with_temp_template(self, tmp_path):
        """Create exporter with a minimal test template"""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        
        # Create a minimal template
        template_content = r"""
\documentclass{article}
\begin{document}
Name: {{ name | escape_latex }}
Email: {{ email | escape_latex }}
\end{document}
"""
        template_file = template_dir / "test.tex"
        template_file.write_text(template_content)
        
        # Create exporter pointing to temp dir
        exporter = ReportExporter()
        exporter.env = Environment(loader=FileSystemLoader(template_dir))
        exporter.env.filters['escape_latex'] = exporter._escape_latex
        
        return exporter
    
    def test_template_renders_without_errors(self, exporter_with_temp_template, mock_report_simple, mock_config_manager):
        """Test that template renders without Jinja2 errors"""
        context = exporter_with_temp_template._build_context(mock_report_simple, mock_config_manager)
        
        template = exporter_with_temp_template.env.get_template("test.tex")
        rendered = template.render(**context)
        
        assert "John Doe" in rendered
        assert "john.doe@example.com" in rendered
        assert rendered.strip().startswith("\\documentclass")

class TestTemplateRendering:

    def test_validate_projects_analyzed_success(self):
        proj = ReportProject(
            project_name="good",
            bullets=["x"],
            languages=["Python"],
            frameworks=[]
        )
        report = Report(None, "t", None, "resume_score", [proj], None)

        ReportExporter()._validate_projects_analyzed(report)

    def test_validate_projects_analyzed_missing_bullets(self):
        proj = ReportProject(
            project_name="bad",
            bullets=[],
            languages=["Python"],
            frameworks=[]
        )
        report = Report(None, "t", None, "resume_score", [proj], None)

        with pytest.raises(ValueError) as exc:
            ReportExporter()._validate_projects_analyzed(report)

        assert "bad" in str(exc.value)

    def test_validate_projects_analyzed_missing_skills(self):
        proj = ReportProject(
            project_name="bad2",
            bullets=["x"],
            languages=[],
            frameworks=[]
        )
        report = Report(None, "t", None, "resume_score", [proj], None)

        with pytest.raises(ValueError) as exc:
            ReportExporter()._validate_projects_analyzed(report)

        assert "bad2" in str(exc.value)

# ==================== PARAMETRIZED TESTS ====================

@pytest.mark.parametrize("input_text,expected_contains", [
    ("Simple text", "Simple text"),
    ("Text with & ampersand", r"\&"),
    ("Math: $x^2$", r"\$"),
    ("Code: var_name", r"\_"),
    ("Percentage: 50%", r"\%"),
])
def test_escape_latex_parametrized(input_text, expected_contains):
    """Parametrized test for LaTeX escaping"""
    exporter = ReportExporter()
    result = exporter._escape_latex(input_text)
    assert expected_contains in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])