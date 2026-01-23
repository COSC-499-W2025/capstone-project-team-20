# src/ui/streamlitApp.py
# Mini frontend demo for Project Analyzer (no CLI input prompts)
# - 16 buttons on the main page (no sidebar)
# - Load ZIP via textbox or upload
# - Captures print() output and shows it in the UI
# - Handles options 10/12/15 with Streamlit selectors instead of input()

import io
import os
import zipfile
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr

import streamlit as st

from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager
from src.ZipParser import parse_zip_to_project_folders
from src.analyzers.badge_engine import ProjectAnalyticsSnapshot, assign_badges, build_fun_facts
from datetime import datetime


# ----------------------------
# Page / styling
# ----------------------------
st.set_page_config(page_title="Project Analyzer", layout="wide")

st.markdown(
    """
    <style>
      .pa-card { padding: 1.0rem; border: 1px solid rgba(49,51,63,0.2); border-radius: 16px; }
      .pa-muted { color: rgba(49,51,63,0.7); }
      .pa-small { font-size: 0.92rem; }
      .stButton>button { width: 100%; height: 3.1rem; border-radius: 14px; }
      .pa-divider { margin: 0.75rem 0 0.75rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Project Analyzer")
st.markdown('<div class="pa-muted pa-small">Mini frontend (Streamlit)</div>', unsafe_allow_html=True)

OPTIONS = {
    1: "Analyze Git Repository & Contributions",
    2: "Extract Metadata & File Statistics",
    3: "Categorize Files by Type",
    4: "Print Project Folder Structure",
    5: "Analyze Languages Detected",
    6: "Run All Analyses",
    7: "Analyze New Folder (Load ZIP)",
    8: "Change Selected Users",
    9: "Analyze Skills (Calculates Resume Score)",
    10: "Generate Resume Insights",
    11: "Retrieve Previous Resume Insights",
    12: "Delete Previous Resume Insights",
    13: "Display Previous Results",
    14: "Show Project Timeline (Projects & Skills)",
    15: "Analyze Badges",
    16: "Exit",
}


# ----------------------------
# Helpers
# ----------------------------
def capture_output(fn) -> str:
    """Capture stdout/stderr from analyzer methods that print()."""
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        try:
            fn()
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")
    return buf.getvalue()


def get_analyzer() -> ProjectAnalyzer:
    """Create analyzer once and store in session_state."""
    if "analyzer" not in st.session_state:
        st.session_state.analyzer = ProjectAnalyzer(
            config_manager=ConfigManager(),
            root_folders=[],
            zip_path=Path("."),  # placeholder until ZIP loaded
        )
        st.session_state.zip_loaded = False
        st.session_state.last_output = ""
        st.session_state.selected_option = None
    return st.session_state.analyzer


def require_zip_loaded() -> bool:
    """Return True if ready, else show warning and return False."""
    if not st.session_state.get("zip_loaded", False):
        st.warning("No project ZIP loaded yet. Use **7. Analyze New Folder (Load ZIP)** first.")
        return False
    return True


def refresh_projects(analyzer: ProjectAnalyzer):
    """Warm cache so selectboxes show projects."""
    try:
        analyzer._get_projects()
    except Exception:
        pass


# ----------------------------
# Main state
# ----------------------------
analyzer = get_analyzer()
refresh_projects(analyzer)

# ---- ZIP Gate: force load before showing the menu ----
if "zip_path_str" not in st.session_state:
    st.session_state.zip_path_str = ""

if not st.session_state.get("zip_loaded", False):
    st.subheader("Load Project ZIP to Begin")
    st.write("Paste the **absolute path** to the ZIP your Project Analyzer expects.")

    zip_path_str = st.text_input("Absolute path to ZIP", value=st.session_state.zip_path_str)

    if st.button("Load ZIP", type="primary"):
        zp = Path(zip_path_str).expanduser()

        if not (zp.exists() and zipfile.is_zipfile(zp)):
            st.error("Invalid path or not a zip file.")
        else:
            analyzer.zip_path = zp
            analyzer.root_folders = parse_zip_to_project_folders(zp)
            analyzer.cached_extract_dir = None
            analyzer.cached_projects = []

            out = capture_output(analyzer.initialize_projects)

            st.session_state.zip_loaded = True
            st.session_state.zip_path_str = str(zp)
            st.session_state.last_output = out

            st.success("ZIP loaded! Scroll down to use the menu.")
            st.rerun()  # immediately refresh into the main menu view

    st.stop()  # IMPORTANT: prevents menu buttons from showing before load

# ----------------------------
# Button grid (16 buttons)
# ----------------------------
st.markdown('<div class="pa-divider"></div>', unsafe_allow_html=True)
st.subheader("Menu")

cols = st.columns(4)
for i in range(1, 17):
    c = cols[(i - 1) % 4]
    with c:
        if st.button(f"{i}. {OPTIONS[i]}", key=f"btn_{i}"):
            st.session_state.selected_option = i

selected = st.session_state.get("selected_option", None)

st.markdown('<div class="pa-divider"></div>', unsafe_allow_html=True)

# ----------------------------
# Action panel
# ----------------------------
left, right = st.columns([1.15, 1])

with left:
    st.markdown('<div class="pa-card">', unsafe_allow_html=True)
    if selected is None:
        st.markdown("Pick an option above to get started.")
    else:
        st.markdown(f"### Selected: {selected}. {OPTIONS[selected]}")

        # ----------------------------
        # Option 16: Exit
        # ----------------------------
        if selected == 16:
            st.success("Exit selected. (Nothing to do in Streamlit.)")
            st.session_state.selected_option = None

        # ----------------------------
        # Option 7: Load ZIP (textbox or upload)
        # ----------------------------
        elif selected == 7:
            st.subheader("Change Project ZIP")
            zip_path_str = st.text_input("Absolute path to ZIP", value=st.session_state.get("zip_path_str", ""))

            if st.button("Load new ZIP", type="primary"):
                zp = Path(zip_path_str).expanduser()

                if not (zp.exists() and zipfile.is_zipfile(zp)):
                    st.error("Invalid path or not a zip file.")
                else:
                    analyzer.zip_path = zp
                    analyzer.root_folders = parse_zip_to_project_folders(zp)
                    analyzer.cached_extract_dir = None
                    analyzer.cached_projects = []

                    out = capture_output(analyzer.initialize_projects)

                    st.session_state.zip_loaded = True
                    st.session_state.zip_path_str = str(zp)
                    st.session_state.last_output = out

                    st.success("New ZIP loaded and projects initialized.")

        # ----------------------------
        # Option 8: Change Selected Users (no input() prompts)
        # ----------------------------
        elif selected == 8:
            if not require_zip_loaded():
                st.stop()

            current = analyzer._config_manager.get("usernames") or []
            st.write("Set the usernames used for Git contribution analysis.")
            usernames_text = st.text_input("Comma-separated usernames", value=", ".join(current))
            if st.button("Save usernames", type="primary"):
                usernames = [u.strip() for u in usernames_text.split(",") if u.strip()]
                analyzer._config_manager.set("usernames", sorted(list(set(usernames))))
                st.success("Saved.")
                st.session_state.last_output = f"Saved usernames: {', '.join(usernames) if usernames else '(none)'}"

        # ----------------------------
        # Option 10: Generate Resume Insights (Streamlit selection instead of input())
        # ----------------------------
        elif selected == 10:
            if not require_zip_loaded():
                st.stop()

            # ensure scores exist
            out1 = capture_output(analyzer._ensure_scores_are_calculated)
            refresh_projects(analyzer)

            all_projects = analyzer._get_projects()
            scored = [p for p in all_projects if getattr(p, "resume_score", 0) and p.resume_score > 0]
            if not scored:
                st.warning("No scored projects found. Run **9. Analyze Skills** first.")
                st.session_state.last_output = out1
            else:
                scored_sorted = sorted(scored, key=lambda p: p.resume_score, reverse=True)

                mode = st.radio(
                    "Generate for",
                    ["Single project", "Top 3 projects", "All scored projects"],
                    horizontal=True,
                    key="insights_mode",
                )

                selected_projects = []
                if mode == "Single project":
                    name = st.selectbox("Project", [p.name for p in scored_sorted], key="insights_project")
                    selected_projects = [next(p for p in scored_sorted if p.name == name)]
                elif mode == "Top 3 projects":
                    selected_projects = scored_sorted[:3]
                else:
                    selected_projects = scored_sorted

                if st.button("Generate insights", type="primary"):
                    buf = io.StringIO()
                    with redirect_stdout(buf), redirect_stderr(buf):
                        # run prerequisites + generation (same logic as your CLI flow)
                        for proj in selected_projects:
                            if not getattr(proj, "categories", None) or not getattr(proj, "num_files", None) or not getattr(proj, "languages", None):
                                analyzer.analyze_metadata(projects=[proj])
                                analyzer.analyze_categories(projects=[proj])
                                analyzer.analyze_languages(projects=[proj])

                            analyzer._generate_insights_for_project(proj)

                    st.session_state.last_output = out1 + "\n" + buf.getvalue()
                    st.success("Insights generated (see Output panel).")

        # ----------------------------
        # Option 12: Delete Previous Resume Insights (Streamlit selection)
        # ----------------------------
        elif selected == 12:
            if not require_zip_loaded():
                st.stop()

            projects = analyzer._get_projects()
            if not projects:
                st.warning("No projects found.")
            else:
                name = st.selectbox("Project", [p.name for p in projects], key="del_insights_project")
                if st.button("Delete insights", type="primary"):
                    proj = next(p for p in projects if p.name == name)
                    proj.bullets, proj.summary = [], ""
                    analyzer.project_manager.set(proj)
                    st.session_state.last_output = f"Deleted insights for {proj.name}."
                    st.success("Deleted.")

        # ----------------------------
        # Option 15: Analyze Badges (Streamlit selection)
        # ----------------------------
        elif selected == 15:
            if not require_zip_loaded():
                st.stop()

            projects = analyzer._get_projects()
            if not projects:
                st.warning("No projects found.")
            else:
                name = st.selectbox("Project", [p.name for p in projects], key="badge_project")
                if st.button("Analyze badges", type="primary"):
                    proj = next(p for p in projects if p.name == name)

                    buf = io.StringIO()
                    with redirect_stdout(buf), redirect_stderr(buf):
                        # same prerequisite logic as analyze_badges()
                        if not all([
                            getattr(proj, "num_files", None),
                            getattr(proj, "date_created", None),
                            getattr(proj, "last_modified", None),
                            getattr(proj, "categories", None),
                            getattr(proj, "languages", None),
                            getattr(proj, "skills_used", None),
                        ]):
                            print(f"\n  - Prerequisite data missing for {proj.name}. Running required analyses...")
                            analyzer.analyze_metadata(projects=[proj])
                            analyzer.analyze_categories(projects=[proj])
                            analyzer.analyze_languages(projects=[proj])
                            analyzer.analyze_skills(projects=[proj], silent=True)
                            print(f"  - Prerequisite analyses complete for {proj.name}.")
                            proj = analyzer.project_manager.get_by_name(proj.name)

                        duration_days = (proj.last_modified - proj.date_created).days if proj.last_modified and proj.date_created else 0
                        snapshot = ProjectAnalyticsSnapshot(
                            name=proj.name,
                            total_files=proj.num_files,
                            total_size_kb=proj.size_kb,
                            total_size_mb=(proj.size_kb / 1024) if proj.size_kb else 0,
                            duration_days=duration_days,
                            category_summary={"counts": proj.categories},
                            languages=proj.language_share,
                            skills=set(proj.skills_used),
                            author_count=proj.author_count,
                            collaboration_status=proj.collaboration_status,
                        )
                        badge_ids = assign_badges(snapshot)
                        fun_facts = build_fun_facts(snapshot, badge_ids)

                        print("\nBadges Earned:")
                        if badge_ids:
                            for b in badge_ids:
                                print(f"  - {b}")
                        else:
                            print("  (none)")

                        if fun_facts:
                            print("\nFun Facts:")
                            for fact in fun_facts:
                                print(f"  • {fact}")

                    st.session_state.last_output = buf.getvalue()
                    st.success("Badge analysis complete (see Output panel).")

        # ----------------------------
        # All other options that don't require input()
        # ----------------------------
        else:
            if not require_zip_loaded():
                st.stop()

            menu = {
                1: analyzer.analyze_git_and_contributions,
                2: analyzer.menu_print_metadata_summary,
                3: analyzer.analyze_categories,
                4: analyzer.print_tree,
                5: analyzer.analyze_languages,
                6: analyzer.run_all,
                9: analyzer.analyze_skills,
                11: analyzer.retrieve_previous_insights,
                13: analyzer.display_analysis_results,
                14: analyzer.display_project_timeline,
            }

            action = menu.get(selected)
            if action is None:
                st.info("Not wired yet (or requires special UI).")
            else:
                if st.button("Run", type="primary"):
                    st.session_state.last_output = capture_output(action)
                    st.success("Done (see Output panel).")

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="pa-card">', unsafe_allow_html=True)
    st.markdown("### Output")
    st.code(st.session_state.get("last_output", "") or "(run an option to see output)")
    st.markdown("</div>", unsafe_allow_html=True)
