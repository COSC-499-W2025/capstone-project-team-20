import os
import re
import subprocess
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from src.models.Report import Report
from src.managers.ConfigManager import ConfigManager

class ReportExporter:
    """
    Exports a Report object to a PDF file using LaTeX.
    It uses Jinja2 to populate a LaTeX template with data from the report
    and configuration manager.
    """

    def _escape_latex_filter(self, s: str) -> str:
        """Jinja2 filter to escape LaTeX special characters."""
        if not isinstance(s, str):
            return s
        return s.replace('\\', r'\textbackslash{}') \
                .replace('{', r'\{') \
                .replace('}', r'\}') \
                .replace('#', r'\#') \
                .replace('$', r'\$') \
                .replace('%', r'\%') \
                .replace('&', r'\&') \
                .replace('~', r'\textasciitilde{}') \
                .replace('_', r'\_') \
                .replace('^', r'\textasciicircum{}')

    def export_to_pdf(
        self,
        report: Report,
        config_manager: ConfigManager,
        output_path: str,
        template_name: str,
    ):
        # --- FIX: Add validation to prevent exporting an empty report ---
        if not report or not report.projects:
            raise ValueError("Cannot export a report with no projects.")

        template_dir = Path(__file__).parent.resolve() / "templates"

        if not template_dir.is_dir():
            raise FileNotFoundError(f"Template directory not found at {template_dir}")

        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            block_start_string='\\BLOCK{',
            block_end_string='}',
            variable_start_string='\\VAR{',
            variable_end_string='}',
            comment_start_string='\\#{',
            comment_end_string='}',
            trim_blocks=True,
            lstrip_blocks=True
        )
        env.filters['escape_latex'] = self._escape_latex_filter

        try:
            template = env.get_template(f"{template_name}.tex")
        except Exception as e:
            raise FileNotFoundError(f"Could not load template '{template_name}.tex'. Check that the file exists in the templates directory. Error: {e}")

        context = {
            "report": report,
            "projects": report.projects,
            "name": config_manager.get("name", "Your Name"),
            "email": config_manager.get("email", "your.email@example.com"),
            "phone": config_manager.get("phone", "555-555-5555"),
            "github": config_manager.get("github", "your_github"),
            "linkedin": config_manager.get("linkedin", "your_linkedin"),
            "education": config_manager.get("education", []),
            "experience": config_manager.get("experience", []),
        }

        rendered_latex = template.render(context)

        output_p = Path(output_path)
        output_p.parent.mkdir(parents=True, exist_ok=True)

        latex_filename = output_p.with_suffix('.tex')
        with open(latex_filename, 'w', encoding='utf-8') as f:
            f.write(rendered_latex)

        command = [
            'latexmk',
            '-pdf',
            '-interaction=nonstopmode',
            f'-output-directory={output_p.parent.resolve()}',
            str(latex_filename.resolve())
        ]

        try:
            subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        except FileNotFoundError:
            raise RuntimeError("`latexmk` command not found. Please ensure a full LaTeX distribution (like MiKTeX, TeX Live, or MacTeX) is installed and in your system's PATH.")
        except subprocess.CalledProcessError as e:
            log_filename = latex_filename.with_suffix('.log')
            error_log = ""
            if log_filename.exists():
                with open(log_filename, 'r', encoding='utf-8') as log_file:
                    error_log = log_file.read()

            raise RuntimeError(
                "LaTeX compilation failed. Check the .log file for details.\n"
                f"Command: {' '.join(command)}\n"
                f"Log file content snippet:\n{error_log[-2000:]}"
            )
        finally:
            # Clean up auxiliary files
            cleanup_command = ['latexmk', '-c', f'-output-directory={output_p.parent.resolve()}', str(latex_filename.resolve())]
            try:
                subprocess.run(cleanup_command, check=False, capture_output=True, text=True, encoding='utf-8')
                if latex_filename.exists():
                    os.remove(latex_filename)
            except Exception:
                # Don't let cleanup failures prevent the program from continuing
                pass
