
import io
import zipfile
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
import atexit

import streamlit as st

from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager
from src.ZipParser import parse_zip_to_project_folders
from src.analyzers.badge_engine import ProjectAnalyticsSnapshot, assign_badges, build_fun_facts


# ----------------------------
# Page / styling
# ----------------------------
st.set_page_config(page_title="Project Analyzer", layout="wide")

st.markdown(
    """
    <style>
      .pa-card {
        padding: 1.0rem;
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 18px;
        background: rgba(255,255,255,0.03);
      }
      .pa-muted { color: rgba(255,255,255,0.70); }
      .pa-small { font-size: 0.92rem; }

      .pa-chip {
        display: inline-block;
        padding: 0.35rem 0.70rem;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.05);
        margin-right: 0.45rem;
        font-size: 0.9rem;
      }

      .pa-divider { margin: 0.75rem 0 0.75rem 0; }

      .stButton>button {
        width: 100%;
        height: 2.7rem;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.04);
        font-weight: 650;
      }
      .stButton>button:hover {
        border-color: rgba(255,255,255,0.25);
        background: rgba(255,255,255,0.07);
      }

      pre { border-radius: 14px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Team 20 Project Analyzer")
st.markdown('<div class="pa-muted pa-small">Mini frontend (Streamlit)</div>', unsafe_allow_html=True)

OPTIONS = {
    1: "Analyze Git Repository & Contributions",
    2: "Extract Metadata & File Statistics",
    3: "Categorize Files by Type",
    4: "Print Project Folder Structure",
    5: "Analyze Languages Detected",
    6: "Run All Analyzers",
    7: "Analyze New Project (Change ZIP)",
    8: "Change Selected GitHub Username",
    9: "Analyze Skills (Calculates Resume Score)",
    10: "Generate Resume Insights",
    11: "Retrieve Previous Resume Insights",
    12: "Delete Previous Resume Insights",
    13: "Display Previous Portfolio Information",
    14: "Show Project Timeline (Projects & Skills)",
    15: "Analyze Badges",
    16: "Enter Resume Personal Information",
    17: "Exit",
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

def parse_education_lines(raw: str) -> list[dict]:
    entries: list[dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        while len(parts) < 4:
            parts.append("")
        school, location, degree, dates = parts[:4]
        if any([school, location, degree, dates]):
            entries.append(
                {
                    "school": school,
                    "location": location,
                    "degree": degree,
                    "dates": dates,
                }
            )
    return entries


def parse_experience_lines(raw: str) -> list[dict]:
    entries: list[dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        while len(parts) < 5:
            parts.append("")
        title, company, location, dates, bullets_raw = parts[:5]
        bullets = [b.strip() for b in bullets_raw.split(";") if b.strip()]
        if any([title, company, location, dates, bullets]):
            entries.append(
                {
                    "title": title,
                    "company": company,
                    "location": location,
                    "dates": dates,
                    "bullets": bullets,
                }
            )
    return entries


def format_education_lines(entries: list[dict]) -> str:
    lines = []
    for entry in entries or []:
        lines.append(
            " | ".join(
                [
                    entry.get("school", ""),
                    entry.get("location", ""),
                    entry.get("degree", ""),
                    entry.get("dates", ""),
                ]
            ).strip()
        )
    return "\n".join(line for line in lines if line.strip())


def format_experience_lines(entries: list[dict]) -> str:
    lines = []
    for entry in entries or []:
        bullets = "; ".join(entry.get("bullets", []) or [])
        lines.append(
            " | ".join(
                [
                    entry.get("title", ""),
                    entry.get("company", ""),
                    entry.get("location", ""),
                    entry.get("dates", ""),
                    bullets,
                ]
            ).strip()
        )
    return "\n".join(line for line in lines if line.strip())



def get_analyzer() -> ProjectAnalyzer:
    """Create analyzer once and store in session_state."""
    if "analyzer" not in st.session_state:
        st.session_state.analyzer = ProjectAnalyzer(
            config_manager=ConfigManager(),
            root_folders=[],
            zip_path=Path("."),  # placeholder until ZIP loaded
        )
        st.session_state.zip_loaded = False
        st.session_state.zip_path_str = ""
        st.session_state.last_output = ""
        st.session_state.selected_option = None

        if not st.session_state.get("_cleanup_registered", False):
            def _cleanup():
                try:
                    st.session_state.analyzer._cleanup_temp()
                except Exception:
                    pass

            atexit.register(_cleanup)
            st.session_state._cleanup_registered = True


    return st.session_state.analyzer


def require_zip_loaded() -> bool:
    if not st.session_state.get("zip_loaded", False):
        st.warning("No project ZIP loaded yet. Load one first.")
        return False
    return True


def refresh_projects(analyzer: ProjectAnalyzer):
    try:
        analyzer._get_projects()
    except Exception:
        pass


def load_zip_into_analyzer(analyzer: ProjectAnalyzer, zip_path_str: str) -> str:
    """Load ZIP and initialize projects. Returns captured output."""
    zp = Path(zip_path_str).expanduser()
    if not (zp.exists() and zipfile.is_zipfile(zp)):
        raise ValueError("Invalid path or not a zip file.")
    
    try:
        analyzer._cleanup_temp()
    except Exception:
        pass

    analyzer.zip_path = zp
    analyzer.root_folders = parse_zip_to_project_folders(zp)
    analyzer.cached_extract_dir = None
    analyzer.cached_projects = []

    out = capture_output(analyzer.initialize_projects)
    st.session_state.zip_loaded = True
    st.session_state.zip_path_str = str(zp)
    return out


def go_home(analyzer: ProjectAnalyzer):
    """Return to ZIP gate (home)."""
    try:
        analyzer._cleanup_temp()
    except Exception:
        pass
    st.session_state.zip_loaded = False
    st.session_state.zip_path_str = ""
    st.session_state.selected_option = None
    st.session_state.last_output = ""
    st.rerun()


# ----------------------------
# Main state
# ----------------------------
analyzer = get_analyzer()
refresh_projects(analyzer)

# ---- ZIP Gate: force load before showing the menu ----
if not st.session_state.get("zip_loaded", False):
    st.subheader("Load Project ZIP to Begin")
    st.write("Paste the **absolute path** to the ZIP your Project Analyzer expects.")

    with st.form("load_zip_form", clear_on_submit=False):
        zip_path_str = st.text_input(
            "Absolute path to ZIP",
            value=st.session_state.get("zip_path_str", ""),
            placeholder="/Users/you/path/to/project.zip",
        )
        submitted = st.form_submit_button("Load ZIP")

    if submitted:
        try:
            st.session_state.last_output = load_zip_into_analyzer(analyzer, zip_path_str)
            st.success("ZIP loaded! Redirecting to menu…")
            st.rerun()
        except Exception as e:
            st.error(str(e))


    st.stop()

# ---- Status strip (after ZIP loaded) ----
usernames = analyzer._config_manager.get("usernames") or []
st.markdown(
    f'<span class="pa-chip">📦 ZIP: {st.session_state.get("zip_path_str","")}</span>'
    f'<span class="pa-chip">👤 Users: {(", ".join(usernames) if usernames else "(not set)")}</span>',
    unsafe_allow_html=True,
)

# ----------------------------
# Menu (tabs)
# ----------------------------
st.markdown('<div class="pa-divider"></div>', unsafe_allow_html=True)
st.subheader("Menu")


def set_choice(n: int):
    st.session_state.selected_option = n


tabA, tabB, tabC, tabD = st.tabs(
    ["🔍 Analyzers (1–6)", "⚙️ Setup (7–8)", "📄 Outputs (9–15)", "🚪 Exit"]
)

with tabA:
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("1. Git + Contributions"):
            set_choice(1)
        if st.button("4. Folder Structure"):
            set_choice(4)
    with c2:
        if st.button("2. Metadata + Stats"):
            set_choice(2)
        if st.button("5. Languages"):
            set_choice(5)
    with c3:
        if st.button("3. File Categories"):
            set_choice(3)
        if st.button("6. Run All Analyzers", type="primary"):
            set_choice(6)

with tabB:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("7. Change Project (ZIP)", type="primary"):
            set_choice(7)
        st.caption("Switch the active ZIP project.")
    with c2:
        if st.button("8. Change GitHub Username"):
            set_choice(8)
        st.caption("Set which Git authors count as you.")

with tabC:
    r1 = st.columns(3)
    r2 = st.columns(3)
    r3 = st.columns(3)

    with r1[0]:
        if st.button("9. Skills + Resume Score"):
            set_choice(9)
    with r1[1]:
        if st.button("10. Generate Resume Insights"):
            set_choice(10)
    with r1[2]:
        if st.button("11. Retrieve Resume Insights"):
            set_choice(11)

    with r2[0]:
        if st.button("12. Delete Resume Insights"):
            set_choice(12)
    with r2[1]:
        if st.button("13. Display Portfolio Info"):
            set_choice(13)
    with r2[2]:
        if st.button("14. Project Timeline"):
            set_choice(14)

    with r3[0]:
        if st.button("15. Badges"):
            set_choice(15)
    with r3[1]:
        if st.button("16. Resume Personal Info"):
            set_choice(16)

with tabD:
    if st.button("17. Exit to Home"):
        set_choice(17)

selected = st.session_state.get("selected_option", None)
st.markdown('<div class="pa-divider"></div>', unsafe_allow_html=True)

# ----------------------------
# Action + Output panels (only render when needed)
# ----------------------------
if selected is not None or st.session_state.get("last_output"):
    left, right = st.columns([1.15, 1])

    with left:
        if selected is not None:
            st.markdown('<div class="pa-card">', unsafe_allow_html=True)
            st.markdown(
                f'<span class="pa-chip">Selected: {selected}. {OPTIONS.get(selected, "")}</span>',
                unsafe_allow_html=True,
            )
            st.write("")

            # 17: Exit -> Home
            if selected == 17:
                st.success("Returning to home screen…")
                go_home(analyzer)

            # 7: Change ZIP
            elif selected == 7:
                st.subheader("Change Project ZIP")
                zip_path_str = st.text_input(
                    "Absolute path to ZIP",
                    value=st.session_state.get("zip_path_str", ""),
                    key="change_zip_path",
                )

                if st.button("Load new ZIP", type="primary"):
                    try:
                        st.session_state.last_output = load_zip_into_analyzer(analyzer, zip_path_str)
                        st.success("New ZIP loaded and projects initialized.")
                        refresh_projects(analyzer)
                    except Exception as e:
                        st.error(str(e))

            # 8: Change usernames
                        # 8: Change usernames (MATCHES CLI change_selected_users EXACTLY)
            elif selected == 8:
                st.subheader("Change Selected Users")
                st.write("Please select your username(s) from the list of project contributors:")

                current = analyzer._config_manager.get("usernames") or []

                # Build contributor list the same way CLI does (scan projects -> .git -> get_all_authors)
                projects = analyzer._get_projects()
                all_authors = set()

                if not projects:
                    st.warning("No projects found.")
                else:
                    for project in projects:
                        try:
                            project_path = Path(project.file_path)
                            if (project_path / ".git").exists():
                                with analyzer.suppress_output():
                                    authors = analyzer.contribution_analyzer.get_all_authors(str(project.file_path))
                                if authors:
                                    all_authors.update(authors)
                        except Exception:
                            # keep going like CLI would (it just silently skips via suppress_output)
                            pass

                authors_sorted = sorted(list(all_authors))

                if not authors_sorted:
                    st.warning("No Git authors found in any project.")
                    st.info("Tip: this requires projects to have a real .git folder in the extracted ZIP.")
                else:
                    # UI equivalent of the CLI number selection
                    preselect = [a for a in current if a in authors_sorted]

                    selected_authors = st.multiselect(
                        "Project contributors",
                        options=authors_sorted,
                        default=preselect,
                    )

                    st.caption("You can select multiple contributors.")

                    if st.button("Save usernames", type="primary"):
                        # exact same behavior as CLI: sorted unique
                        new_usernames = sorted(list(set(selected_authors)))

                        if new_usernames:
                            analyzer._config_manager.set("usernames", new_usernames)
                            st.session_state.last_output = (
                                f"Successfully updated selected users to: {', '.join(new_usernames)}"
                            )
                            st.success("Saved.")
                        else:
                            st.session_state.last_output = "No changes made to user selection."
                            st.info("No changes made to user selection.")


            # 10: Generate Resume Insights (selectors)
            elif selected == 10:
                out1 = capture_output(analyzer._ensure_scores_are_calculated)
                refresh_projects(analyzer)

                all_projects = analyzer._get_projects()
                scored = [p for p in all_projects if getattr(p, "resume_score", 0) and p.resume_score > 0]

                if not scored:
                    st.warning("No scored projects found. Run **9. Skills + Resume Score** first.")
                    st.session_state.last_output = out1
                else:
                    scored_sorted = sorted(scored, key=lambda p: p.resume_score, reverse=True)

                    mode = st.radio(
                        "Generate for",
                        ["Single project", "Top 3 projects", "All scored projects"],
                        horizontal=True,
                        key="insights_mode",
                    )

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
                            for proj in selected_projects:
                                if (
                                    not getattr(proj, "categories", None)
                                    or not getattr(proj, "num_files", None)
                                    or not getattr(proj, "languages", None)
                                ):
                                    analyzer.analyze_metadata(projects=[proj])
                                    analyzer.analyze_categories(projects=[proj])
                                    analyzer.analyze_languages(projects=[proj])

                                analyzer._generate_insights_for_project(proj)

                        st.session_state.last_output = out1 + "\n" + buf.getvalue()
                        st.success("Insights generated (see Output panel).")

            # 12: Delete insights (selector)
            elif selected == 12:
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

            # 15: Badges (selector)
            elif selected == 15:
                projects = analyzer._get_projects()
                if not projects:
                    st.warning("No projects found.")
                else:
                    name = st.selectbox("Project", [p.name for p in projects], key="badge_project")
                    if st.button("Analyze badges", type="primary"):
                        proj = next(p for p in projects if p.name == name)

                        buf = io.StringIO()
                        with redirect_stdout(buf), redirect_stderr(buf):
                            if not all(
                                [
                                    getattr(proj, "num_files", None),
                                    getattr(proj, "date_created", None),
                                    getattr(proj, "last_modified", None),
                                    getattr(proj, "categories", None),
                                    getattr(proj, "languages", None),
                                    getattr(proj, "skills_used", None),
                                ]
                            ):
                                print(f"\n  - Prerequisite data missing for {proj.name}. Running required analyses...")
                                analyzer.analyze_metadata(projects=[proj])
                                analyzer.analyze_categories(projects=[proj])
                                analyzer.analyze_languages(projects=[proj])
                                analyzer.analyze_skills(projects=[proj], silent=True)
                                print(f"  - Prerequisite analyses complete for {proj.name}.")
                                proj = analyzer.project_manager.get_by_name(proj.name)

                            duration_days = (
                                (proj.last_modified - proj.date_created).days
                                if proj.last_modified and proj.date_created
                                else 0
                            )
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

            # 16: Resume personal information
            elif selected == 16:
                st.subheader("Resume Personal Information")
                st.caption("Use | to separate fields. Use ; to separate bullets.")

                current_education = analyzer._config_manager.get("education", []) or []
                current_experience = analyzer._config_manager.get("experience", []) or []

                name_value = st.text_input("Full name", value=analyzer._config_manager.get("name", ""))
                email_value = st.text_input("Email", value=analyzer._config_manager.get("email", ""))
                phone_value = st.text_input("Phone", value=analyzer._config_manager.get("phone", ""))
                github_value = st.text_input("GitHub username", value=analyzer._config_manager.get("github", ""))
                linkedin_value = st.text_input("LinkedIn handle", value=analyzer._config_manager.get("linkedin", ""))

                education_value = st.text_area(
                    "Education entries (School | Location | Degree | Dates)",
                    value=format_education_lines(current_education),
                    height=120,
                )
                experience_value = st.text_area(
                    "Experience entries (Title | Company | Location | Dates | Bullet 1; Bullet 2)",
                    value=format_experience_lines(current_experience),
                    height=140,
                )

                if st.button("Save resume info", type="primary"):
                    analyzer._config_manager.set("name", name_value.strip())
                    analyzer._config_manager.set("email", email_value.strip())
                    analyzer._config_manager.set("phone", phone_value.strip())
                    analyzer._config_manager.set("github", github_value.strip())
                    analyzer._config_manager.set("linkedin", linkedin_value.strip())
                    analyzer._config_manager.set("education", parse_education_lines(education_value))
                    analyzer._config_manager.set("experience", parse_experience_lines(experience_value))
                    st.session_state.last_output = "Resume personal information saved."
                    st.success("Saved.")

            # All other options (no input)
            else:
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
        if st.session_state.get("last_output"):
            st.markdown('<div class="pa-card">', unsafe_allow_html=True)
            st.markdown("### Output")
            st.code(st.session_state.get("last_output", "") or "(run an option to see output)")
            st.markdown("</div>", unsafe_allow_html=True)
