from dataclasses import dataclass, field
from typing import List, Optional
from src.analyzers.skill_extractor import SkillExtractor

@dataclass
class PFFile:
    name: str
    path: str
    bytes_: bytes

@dataclass
class PFFolder:
    name: str
    children: List[PFFile] = field(default_factory=list)
    subdir: List["PFFolder"] = field(default_factory=list)


def _get_path(f: PFFile) -> str:
    return f.path

def _get_bytes(f: PFFile, limit: int) -> bytes:
    return f.bytes_[:limit]


def test_extract_from_project_folder():
    # Build a mini in-memory tree with diverse hints
    root = PFFolder("root")
    # Python requirements
    root.children.append(PFFile("requirements.txt", "root/requirements.txt", b"numpy==1.26\npytest==7.0\n"))
    # Java Maven
    root.children.append(PFFile("pom.xml", "root/pom.xml", b"<project><groupId>org.springframework</groupId><artifactId>x</artifactId></project>"))
    # C++ snippet (gtest include)
    root.children.append(PFFile("test.cc", "root/test.cc", b"#include <gtest/gtest.h>\nint main(){}"))
    # C# project with ASP.NET
    root.children.append(PFFile("web.csproj", "root/web.csproj", b"<Project><ItemGroup><PackageReference Include=\"Microsoft.AspNetCore\" /></ItemGroup></Project>"))
    # Node/React signals
    pkg_bytes = b'{"dependencies":{"react":"18.2.0"},"devDependencies":{"jest":"29.0.0"}}'
    root.children.append(PFFile("package.json", "root/app/package.json", pkg_bytes))
    root.children.append(PFFile("webpack.config.js", "root/app/webpack.config.js", b"module.exports = {}"))

    extr = SkillExtractor()
    items = extr.extract_from_project_folder(root, _get_path, _get_bytes)

    skills = {i.skill for i in items}
    assert {"NumPy", "PyTest"}.issubset(skills)
    assert {"Maven", "Spring", "JUnit"}.issubset(skills)
    assert {"C++"}.issubset(skills)
    assert {".NET", "ASP.NET"}.issubset(skills)
    assert {"React", "Webpack"}.issubset(skills)

    # Confidence is bounded (merging logic); ensure reasonable ordering signal exists
    for it in items:
        assert 0.0 < it.confidence <= 0.98
