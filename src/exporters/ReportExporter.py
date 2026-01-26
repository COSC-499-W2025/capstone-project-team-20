from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import subprocess
import shutil

class ReportExporter:
    """Exports Report objects to PDF resumes using LaTeX templates"""
    
    def __init__(self):
        # Set up Jinja2 to load templates from src/exporters/templates/
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(loader=FileSystemLoader(template_dir))
        # Add custom filter for LaTeX escaping
        self.env.filters['escape_latex'] = self._escape_latex
    
    def export_to_pdf(self, report, config_manager, output_path: str = "resume.pdf", template: str = "jake"):
        """
        Generate PDF resume from Report.
        
        Args:
            report: Report object with projects
            config_manager: ConfigManager for user info
            output_path: Where to save PDF (e.g., "resume.pdf")
            template: Template name (default: "jake")
        """
        # 1. Prepare data for template (data will be escaped in template)
        context = self._build_context(report, config_manager)
        
        # 2. Load and render template
        template_obj = self.env.get_template(f"{template}.tex")
        latex_content = template_obj.render(**context)
        
        # 3. Write to .tex file
        output_path = Path(output_path)
        tex_path = output_path.with_suffix('.tex')
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        
        # 4. Compile to PDF
        self._compile_to_pdf(tex_path, output_path)
        
        print(f"✅ Resume exported to {output_path}")
    
    def _build_context(self, report, config_manager):
        """Build the data dictionary for the template"""
        
        # Get user info from config
        name = config_manager.get("name", "Your Name")
        email = config_manager.get("email", "example@email.com")
        phone = config_manager.get("phone", "123-456-6789")
        github = config_manager.get("github", "username")
        linkedin = config_manager.get("linkedin", "")
        
        # Build URLs (these don't need escaping as they're in \href commands)
        github_url = f"https://github.com/{github}" if github else ""
        github_display = f"github.com/{github}" if github else ""
        linkedin_url = f"https://linkedin.com/in/{linkedin}" if linkedin else ""
        linkedin_display = f"linkedin.com/in/{linkedin}" if linkedin else ""
        
        # TODO: Allow user to input this
        education = []
        
        # TODO: Allow user to input this
        experience = []
        
        # Projects from report
        projects = []
        for proj in report.projects:
            # Build tech stack string
            stack_parts = []
            if proj.languages:
                stack_parts.extend(proj.languages)
            if proj.frameworks:
                stack_parts.extend(proj.frameworks)
            stack = ", ".join(stack_parts)
            
            # Format dates
            dates = ""
            if proj.date_created and proj.last_modified:
                dates = f"{proj.date_created.strftime('%b %Y')} - {proj.last_modified.strftime('%b %Y')}"
            elif proj.date_created:
                dates = proj.date_created.strftime('%b %Y')
            
            projects.append({
                "name": proj.project_name,
                "stack": stack,
                "dates": dates,
                "bullets": proj.bullets
            })
        
        # Skills (aggregate from all projects)
        all_languages = set()
        all_frameworks = set()
        for proj in report.projects:
            if proj.languages:
                all_languages.update(proj.languages)
            if proj.frameworks:
                all_frameworks.update(proj.frameworks)
        
        skills = {}
        if all_languages:
            skills["Languages"] = sorted(all_languages)
        if all_frameworks:
            skills["Frameworks"] = sorted(all_frameworks)
        
        return {
            "name": name,
            "email": email,
            "phone": phone,
            "github_url": github_url,
            "github_display": github_display,
            "linkedin_url": linkedin_url,
            "linkedin_display": linkedin_display,
            "education": education,
            "experience": experience,
            "projects": projects,
            "skills": skills
        }
    
    def _escape_latex(self, text):
        """Escape LaTeX special characters in user-provided text"""
        if not text:
            return ""
        
        # Characters that need escaping in LaTeX
        replacements = {
            '\\': r'\textbackslash{}',  # Must be first!
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
    
    def _compile_to_pdf(self, tex_path, output_path):
        """Run pdflatex to compile .tex to .pdf"""
        try:
            # Convert to absolute paths
            tex_path = tex_path.resolve()
            output_path = output_path.resolve()
            
            # Run pdflatex twice for proper formatting (first pass for references)
            for _ in range(2):
                result = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', tex_path.name],
                    capture_output=True,
                    text=True,
                    cwd=tex_path.parent
                )
                
                if result.returncode != 0:
                    # Print last 20 lines of output for debugging
                    error_lines = result.stdout.split('\n')[-20:]
                    raise RuntimeError(
                        f"pdflatex failed:\n" + '\n'.join(error_lines)
                    )
            
            # Move generated PDF to desired location
            generated_pdf = tex_path.with_suffix('.pdf')
            if generated_pdf != output_path:
                shutil.move(str(generated_pdf), str(output_path))
            
            # Clean up auxiliary files
            for ext in ['.aux', '.log', '.out']:
                aux_file = tex_path.with_suffix(ext)
                if aux_file.exists():
                    aux_file.unlink()
            
        except FileNotFoundError:
            raise RuntimeError(
                "pdflatex not found. Please install LaTeX:\n"
                "  macOS: brew install --cask mactex-no-gui\n"
                "  Ubuntu: sudo apt-get install texlive-latex-base\n"
                "  Windows: https://miktex.org/download"
            )