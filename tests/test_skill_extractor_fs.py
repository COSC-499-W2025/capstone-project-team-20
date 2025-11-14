from pathlib import Path
from src.analyzers.skill_extractor import SkillExtractor

def test_skill_extractor_on_filesystem(tmp_path: Path):
    # Create a tiny mixed project
    # JS: package.json with React + scripts; config: vite.config.ts
    pkg = {
        "dependencies": {"react": "^18.2.0", "next": "14.0.0"},
        "devDependencies": {"vitest": "^1.0.0", "eslint": "^8.0.0"},
        "scripts": {"test": "vitest run", "lint": "eslint ."}
    }
    (tmp_path / "package.json").write_text(__import__("json").dumps(pkg))
    (tmp_path / "vite.config.ts").write_text("export default {};")
    # Python: a small module and pyproject with FastAPI + Poetry
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "main.py").write_text("from fastapi import FastAPI\ndef f():\n    pass\n")
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname='x'\n[project]\ndependencies=['fastapi']\n")
    # CMake signal
    (tmp_path / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.25)\n")

    extr = SkillExtractor()
    items = extr.extract_from_path(tmp_path)

    skills = {i.skill for i in items}
    # Language + frameworks/tools should be inferred
    assert "JavaScript" in skills or "TypeScript" in skills
    assert "React" in skills
    assert "Next.js" in skills
    assert "Vite" in skills
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "CMake" in skills

    # Evidence sanity check: make sure multiple sources are contributing
    react = next(i for i in items if i.skill == "React")
    sources = {e.source for e in react.evidence}
    assert {"dependency", "import_statement"}.intersection(sources) or {"dependency", "framework_convention"}.intersection(sources)
