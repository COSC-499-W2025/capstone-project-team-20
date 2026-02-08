from __future__ import annotations
from src.models.Report import Report
from src.models.ReportProject import ReportProject

from typing import Any, Dict, List, Tuple



class ReportEditor:
    """
    CLI editor for a Report and ConfigManager.

    Edits in-place:
    - config_manager: header, education, experience, skills
    - report.projects: project_name, bullets, reorder
    """


    # -------------------------
    # Public entry
    # -------------------------

    def edit_report_cli(self, report: Report, config_manager) -> bool:
        """
        Edits:
        - config_manager: name/email/phone/github/linkedin, education, experience
        - report.projects: project_name, bullets, reorder projects
        Returns True if user finished (you can treat as "edited"), False if cancelled.
        """
        while True:
            print("\n==============================")
            print(" Report Editor")
            print("==============================")
            print("1) Edit header (name/email/phone/github/linkedin)")
            print("2) Edit report projects (name + bullets + reorder)")
            print("3) Edit education")
            print("4) Edit experience")
            print("5) Edit technical skills")
            print("q) Done")
            top = input("> ").strip().lower()

            if top == "q":
                return True

            if top == "1":
                self._edit_header_in_config(config_manager)
                continue

            if top == "2":
                self._edit_report_projects_menu(report.projects)
                continue

            if top == "3":
                self._edit_education_in_config(config_manager)
                continue

            if top == "4":
                self._edit_experience_in_config(config_manager)
                continue

            if top == "5":
                self._edit_skills_menu(config_manager)
                continue

            print("Invalid selection.")

    def _edit_header_in_config(self, config_manager) -> None:
        print("\n--- Edit Header ---")

        def prompt(key: str, label: str) -> None:
            cur = (config_manager.get(key, "") or "").strip()
            v = input(f"{label} [{cur}]: ").strip()
            if v:
                config_manager.set(key, v)

        prompt("name", "name")
        prompt("email", "email")
        prompt("phone", "phone")

        # github
        cur_g = (config_manager.get("github", "") or "").strip()
        raw_g = input(f"github username/url [{cur_g}]: ").strip()
        if raw_g:
            url, disp = self._normalize_github(raw_g)
            handle = disp.replace("github.com/", "").strip("/")
            config_manager.set("github", handle)       # ✅ store username only
            config_manager.set("github_url", url)      # optional (full URL)

        # linkedin
        cur_l = (config_manager.get("linkedin", "") or "").strip()
        raw_l = input(f"linkedin handle/url [{cur_l}]: ").strip()
        if raw_l:
            url, disp = self._normalize_linkedin(raw_l)
            handle = disp.replace("linkedin.com/in/", "").strip("/")
            config_manager.set("linkedin", handle)     # ✅ store handle only
            config_manager.set("linkedin_url", url)


    def _normalize_github(self, raw: str) -> Tuple[str, str]:
        raw = raw.strip()

        # Full URL
        if raw.startswith("http://") or raw.startswith("https://"):
            url = raw
            disp = raw.replace("https://", "").replace("http://", "").rstrip("/")
            return url.rstrip("/"), disp

        # Possibly "github.com/user"
        raw = raw.replace("github.com/", "").strip().strip("/")
        handle = raw
        url = f"https://github.com/{handle}"
        disp = f"github.com/{handle}"
        return url, disp

    def _normalize_linkedin(self, raw: str) -> Tuple[str, str]:
        raw = raw.strip()

        # Full URL
        if raw.startswith("http://") or raw.startswith("https://"):
            url = raw.rstrip("/")
            disp = raw.replace("https://", "").replace("http://", "").rstrip("/")
            return url, disp

        # Possibly "linkedin.com/in/handle"
        raw = raw.replace("linkedin.com/in/", "").strip().strip("/")
        handle = raw
        url = f"https://linkedin.com/in/{handle}"
        disp = f"linkedin.com/in/{handle}"
        return url, disp

    # -------------------------
    # Projects
    # -------------------------

    def _edit_report_projects_menu(self, projects: List[ReportProject]) -> None:
        if not projects:
            print("No projects found to edit.")
            return

        while True:
            print("\n--- Report Projects ---")
            print("1) Rename project")
            print("2) Edit project bullets")
            print("3) Reorder projects")
            print("4) Back")
            sub = input("> ").strip()

            if sub == "1":
                self._pick_report_project_and_rename(projects)
            elif sub == "2":
                self._pick_report_project_and_edit_bullets(projects)
            elif sub == "3":
                self._reorder_list_cli(
                    items=projects,
                    label_getter=lambda p: p.project_name,
                    title="Reorder Projects",
                )
            elif sub == "4":
                return
            else:
                print("Invalid selection.")

    def _edit_bullets_cli(self, project_name: str, bullets: List[str]) -> None:
        while True:
            print(f"\n--- Bullets for {project_name} ---")
            if not bullets:
                print("(none)")
            for j, b in enumerate(bullets, 1):
                print(f"  {j}) {b}")

            print("\nOptions:")
            print("  1) Edit bullet")
            print("  2) Add bullet")
            print("  3) Delete bullet")
            print("  4) Move bullet up/down")
            print("  5) Back")
            sub = input("> ").strip()

            if sub == "1":
                n = input("Bullet # to edit: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(bullets):
                    new_txt = input("New text: ").strip()
                    if new_txt:
                        bullets[int(n) - 1] = new_txt
                else:
                    print("Invalid bullet number.")

            elif sub == "2":
                new_txt = input("New bullet: ").strip()
                if new_txt:
                    bullets.append(new_txt)

            elif sub == "3":
                n = input("Bullet # to delete: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(bullets):
                    bullets.pop(int(n) - 1)
                else:
                    print("Invalid bullet number.")

            elif sub == "4":
                n = input("Bullet # to move: ").strip()
                if not (n.isdigit() and 1 <= int(n) <= len(bullets)):
                    print("Invalid bullet number.")
                    continue
                direction = input("u=up, d=down: ").strip().lower()
                i = int(n) - 1
                if direction == "u" and i > 0:
                    bullets[i - 1], bullets[i] = bullets[i], bullets[i - 1]
                elif direction == "d" and i < len(bullets) - 1:
                    bullets[i + 1], bullets[i] = bullets[i], bullets[i + 1]
                else:
                    print("Can't move that way.")

            elif sub == "5":
                return

            else:
                print("Invalid selection.")

    # -------------------------
    # Education
    # -------------------------
    def _edit_education_in_config(self, config_manager) -> None:
        edu: List[Dict[str, Any]] = config_manager.get("education", []) or []
        # reuse your existing menu logic but operate on edu list
        self._edit_education_list_cli(edu)
        config_manager.set("education", edu)

    def _edit_education_list_cli(self, edu: List[Dict[str, Any]]) -> None:
        while True:
            print("\n--- Education ---")
            if not edu:
                print("(none)")
            else:
                for i, e in enumerate(edu, 1):
                    school = e.get("school", "")
                    degree = e.get("degree", "")
                    dates = e.get("dates", "")
                    print(f"  {i}) {school} — {degree} ({dates})")

            print("\nOptions:")
            print("  1) Add entry")
            print("  2) Edit entry")
            print("  3) Delete entry")
            print("  4) Reorder entries")
            print("  5) Back")
            sub = input("> ").strip()

            if sub == "1":
                edu.append(self._prompt_education_entry({}))

            elif sub == "2":
                if not edu:
                    print("No entries to edit.")
                    continue
                n = input("Entry # to edit: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(edu):
                    idx = int(n) - 1
                    edu[idx] = self._prompt_education_entry(edu[idx])
                else:
                    print("Invalid entry number.")

            elif sub == "3":
                if not edu:
                    print("No entries to delete.")
                    continue
                n = input("Entry # to delete: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(edu):
                    edu.pop(int(n) - 1)
                else:
                    print("Invalid entry number.")

            elif sub == "4":
                self._reorder_list_cli(edu, lambda e: e.get("school", "School"), "Reorder Education")

            elif sub == "5":
                return

            else:
                print("Invalid selection.")

    def _prompt_education_entry(self, cur: Dict[str, Any]) -> Dict[str, Any]:
        school = input(f"School [{cur.get('school','')}]: ").strip()
        location = input(f"Location [{cur.get('location','')}]: ").strip()
        degree = input(f"Degree [{cur.get('degree','')}]: ").strip()
        dates = input(f"Dates [{cur.get('dates','')}]: ").strip()

        out = dict(cur)
        if school: out["school"] = school
        if location: out["location"] = location
        if degree: out["degree"] = degree
        if dates: out["dates"] = dates
        return out

    # -------------------------
    # Experience
    # -------------------------

    def _edit_experience_in_config(self, config_manager) -> None:
        exp: List[Dict[str, Any]] = config_manager.get("experience", []) or []
        self._edit_experience_list_cli(exp)
        config_manager.set("experience", exp)

    def _edit_experience_list_cli(self, exp: List[Dict[str, Any]]) -> None:
        while True:
            print("\n--- Experience ---")
            if not exp:
                print("(none)")
            else:
                for i, j in enumerate(exp, 1):
                    title = j.get("title", "")
                    company = j.get("company", "")
                    dates = j.get("dates", "")
                    print(f"  {i}) {title} @ {company} ({dates})")

            print("\nOptions:")
            print("  1) Add job")
            print("  2) Edit job")
            print("  3) Delete job")
            print("  4) Reorder jobs")
            print("  5) Back")
            sub = input("> ").strip()

            if sub == "1":
                exp.append(self._prompt_experience_entry({}))

            elif sub == "2":
                if not exp:
                    print("No jobs to edit.")
                    continue
                n = input("Job # to edit: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(exp):
                    idx = int(n) - 1
                    exp[idx] = self._prompt_experience_entry(exp[idx])
                else:
                    print("Invalid job number.")

            elif sub == "3":
                if not exp:
                    print("No jobs to delete.")
                    continue
                n = input("Job # to delete: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(exp):
                    exp.pop(int(n) - 1)
                else:
                    print("Invalid job number.")

            elif sub == "4":
                self._reorder_list_cli(exp, lambda j: j.get("title", "Job"), "Reorder Experience")

            elif sub == "5":
                return

            else:
                print("Invalid selection.")


    def _prompt_experience_entry(self, cur: Dict[str, Any]) -> Dict[str, Any]:
        title = input(f"Title [{cur.get('title','')}]: ").strip()
        company = input(f"Company [{cur.get('company','')}]: ").strip()
        location = input(f"Location [{cur.get('location','')}]: ").strip()
        dates = input(f"Dates [{cur.get('dates','')}]: ").strip()

        bullets = list(cur.get("bullets", []) or [])
        print("\nEdit bullets for this job:")
        self._edit_bullets_cli(cur.get("title", "Job"), bullets)

        out = dict(cur)
        if title:
            out["title"] = title
        if company:
            out["company"] = company
        if location:
            out["location"] = location
        if dates:
            out["dates"] = dates
        out["bullets"] = bullets
        return out

    # -------------------------
    # Skills
    # -------------------------

    def _edit_skills_menu(self, config_manager) -> None:
        skills: Dict[str, List[str]] = config_manager.get("skills", {}) or {}

        while True:
            print("\n--- Technical Skills ---")
            if not skills:
                print("(none)")
            else:
                for k in sorted(skills.keys(), key=lambda s: s.lower()):
                    print(f"  - {k}: {', '.join(skills.get(k, []) or [])}")

            print("\nOptions:")
            print("  1) Add category")
            print("  2) Rename category")
            print("  3) Delete category")
            print("  4) Edit items in a category")
            print("  5) Back")
            sub = input("> ").strip()

            if sub == "1":
                name = input("New category name: ").strip()
                if name:
                    skills.setdefault(name, [])
                    config_manager.set("skills", skills)

            elif sub == "2":
                old = input("Category to rename: ").strip()
                if old in skills:
                    new = input(f"Rename '{old}' to: ").strip()
                    if new and new not in skills:
                        skills[new] = skills.pop(old)
                        config_manager.set("skills", skills)
                else:
                    print("Category not found.")

            elif sub == "3":
                name = input("Category to delete: ").strip()
                if name in skills:
                    del skills[name]
                    config_manager.set("skills", skills)
                else:
                    print("Category not found.")

            elif sub == "4":
                name = input("Category to edit: ").strip()
                if name not in skills:
                    print("Category not found.")
                    continue
                self._edit_skill_items_cli(name, skills[name])
                config_manager.set("skills", skills)

            elif sub == "5":
                return
            else:
                print("Invalid selection.")


    def _edit_skill_items_cli(self, category: str, items: List[str]) -> None:
        while True:
            print(f"\n--- {category} ---")
            if not items:
                print("(none)")
            for i, it in enumerate(items, 1):
                print(f"  {i}) {it}")

            print("\nOptions:")
            print("  1) Add item")
            print("  2) Edit item")
            print("  3) Delete item")
            print("  4) Move item up/down")
            print("  5) Back")
            sub = input("> ").strip()

            if sub == "1":
                v = input("New item: ").strip()
                if v:
                    items.append(v)

            elif sub == "2":
                n = input("Item # to edit: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(items):
                    v = input("New text: ").strip()
                    if v:
                        items[int(n) - 1] = v
                else:
                    print("Invalid item number.")

            elif sub == "3":
                n = input("Item # to delete: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(items):
                    items.pop(int(n) - 1)
                else:
                    print("Invalid item number.")

            elif sub == "4":
                n = input("Item # to move: ").strip()
                if not (n.isdigit() and 1 <= int(n) <= len(items)):
                    print("Invalid item number.")
                    continue
                direction = input("u=up, d=down: ").strip().lower()
                i = int(n) - 1
                if direction == "u" and i > 0:
                    items[i - 1], items[i] = items[i], items[i - 1]
                elif direction == "d" and i < len(items) - 1:
                    items[i + 1], items[i] = items[i], items[i + 1]
                else:
                    print("Can't move that way.")

            elif sub == "5":
                return

            else:
                print("Invalid selection.")

    def _pick_report_project_and_rename(self, projects: List[ReportProject]) -> None:
        print("\nSelect a project to rename:")
        for i, p in enumerate(projects, 1):
            print(f"  {i}) {p.project_name}")
        print("  q) Back")

        pick = input("> ").strip().lower()
        if pick == "q":
            return
        if not pick.isdigit():
            print("Please enter a number or q.")
            return

        idx = int(pick) - 1
        if not (0 <= idx < len(projects)):
            print("Invalid project number.")
            return

        cur = projects[idx].project_name
        new_name = input(f"New name [{cur}]: ").strip()
        if new_name:
            projects[idx].project_name = new_name


    def _pick_report_project_and_edit_bullets(self, projects: List[ReportProject]) -> None:
        print("\nSelect a project to edit bullets:")
        for i, p in enumerate(projects, 1):
            print(f"  {i}) {p.project_name}")
        print("  q) Back")

        pick = input("> ").strip().lower()
        if pick == "q":
            return
        if not pick.isdigit():
            print("Please enter a number or q.")
            return

        idx = int(pick) - 1
        if not (0 <= idx < len(projects)):
            print("Invalid project number.")
            return

        proj = projects[idx]
        bullets = list(proj.bullets or [])
        self._edit_bullets_cli(proj.project_name, bullets)
        proj.bullets = bullets


    # -------------------------
    # Generic reorder helper
    # -------------------------

    def _reorder_list_cli(self, items: List[Any], label_getter, title: str) -> None:
        """
        Simple reorder UI:
          - type: "from,to" (1-indexed)
          - moves one element to a new position
        """
        if len(items) < 2:
            print("Nothing to reorder.")
            return

        while True:
            print(f"\n--- {title} ---")
            for i, it in enumerate(items, 1):
                print(f"  {i}) {label_getter(it)}")
            print("Enter move as 'from,to' (example: 3,1), or 'q' to stop.")
            raw = input("> ").strip().lower()
            if raw == "q":
                return
            if "," not in raw:
                print("Invalid format.")
                continue
            a, b = [x.strip() for x in raw.split(",", 1)]
            if not (a.isdigit() and b.isdigit()):
                print("Invalid numbers.")
                continue
            frm = int(a) - 1
            to = int(b) - 1
            if not (0 <= frm < len(items) and 0 <= to < len(items)):
                print("Out of range.")
                continue
            item = items.pop(frm)
            items.insert(to, item)
