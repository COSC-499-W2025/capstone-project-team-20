from typing import Any, Dict


def set_project_analysis_values(
    project: Any,
    stats: Dict[str, Any],
    dimensions: Dict[str, Any],
    tech_profile: Dict[str, Any],
) -> None:
    """
    Populate a Project instance from analysis outputs.

    This keeps ProjectAnalyzer.analyze_skills small and makes the logic
    reusable from other places if needed.
    """
    overall = stats.get("overall", {}) or {}
    per_lang = stats.get("per_language", {}) or {}

    # Overall metrics
    project.total_loc = overall.get("total_lines_of_code", 0)
    project.comment_ratio = overall.get("comment_ratio", 0.0)
    project.test_file_ratio = overall.get("test_file_ratio", 0.0)
    project.avg_functions_per_file = overall.get("avg_functions_per_file", 0.0)
    project.max_function_length = overall.get("max_function_length", 0)

    # Primary languages by LOC (ignore tiny ones)
    project.primary_languages = [
        lang
        for lang, data in sorted(
            per_lang.items(),
            key=lambda kv: kv[1].get("total_lines_of_code", 0),
            reverse=True,
        )
        if data.get("total_lines_of_code", 0) >= 100
    ]

    # Dimensions
    td = dimensions.get("testing_discipline", {}) or {}
    project.testing_discipline_level = td.get("level", "")
    project.testing_discipline_score = td.get("score", 0.0)

    doc = dimensions.get("documentation_habits", {}) or {}
    project.documentation_habits_level = doc.get("level", "")
    project.documentation_habits_score = doc.get("score", 0.0)

    mod = dimensions.get("modularity", {}) or {}
    project.modularity_level = mod.get("level", "")
    project.modularity_score = mod.get("score", 0.0)

    ld = dimensions.get("language_depth", {}) or {}
    project.language_depth_level = ld.get("level", "")
    project.language_depth_score = ld.get("score", 0.0)

    # Tech-profile fields from SkillAnalyzer
    project.frameworks = tech_profile.get("frameworks", [])
    project.dependencies_list = tech_profile.get("dependencies_list", [])
    project.dependency_files_list = tech_profile.get("dependency_files_list", [])
    project.build_tools = tech_profile.get("build_tools", [])

    project.has_dockerfile = bool(tech_profile.get("has_dockerfile", False))
    project.has_database = bool(tech_profile.get("has_database", False))
    project.has_frontend = bool(tech_profile.get("has_frontend", False))
    project.has_backend = bool(tech_profile.get("has_backend", False))
    project.has_test_files = bool(tech_profile.get("has_test_files", False))
    project.has_readme = bool(tech_profile.get("has_readme", False))
    project.readme_keywords = tech_profile.get("readme_keywords", [])
